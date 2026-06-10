"""
Orchestrator — local mode (no Docker).

Agents run as direct subprocesses: `opencode run "<prompt>"`.
Each agent's agent.md is injected via the `instructions` field in opencode.json
(generated per-worktree). Git worktree + PR workflow stays identical to server.py.

Model: google/gemma-4-31b-it via Google Generative AI API.
Auth: env var GOOGLE_GENERATIVE_AI_API_KEY.

Usage:
    cd orchestrator
    pip install -r requirements.txt
    python local_server.py
"""
import os, re, uuid, json, logging, subprocess, urllib.request, pathlib
from typing import Optional
from urllib.parse import urlparse

# Load .env from project root if available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("orchestrator-local")

# ---------- Paths ----------
ROOT = pathlib.Path(__file__).parent.parent
AGENTS_DIR = ROOT / "agents"

AGENTS = {
    "planner":      AGENTS_DIR / "planner",
    "be-engineer":  AGENTS_DIR / "be-engineer",
    "fe-engineer":  AGENTS_DIR / "fe-engineer",
    "reviewer":     AGENTS_DIR / "reviewer",
    "qc-engineer":  AGENTS_DIR / "qc-engineer",
}


# ---------- Config from env ----------
GOOGLE_GENERATIVE_AI_API_KEY = os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY", "")
GITHUB_TOKEN                 = os.environ.get("GITHUB_TOKEN", "")
WORK_ROOT                    = os.environ.get("WORK_ROOT", str(ROOT / "work"))
DEFAULT_REPO                 = os.environ.get("DEFAULT_REPO", "")
DEFAULT_BASE_BRANCH          = os.environ.get("DEFAULT_BASE_BRANCH", "main")
OPENCODE_MODEL               = os.environ.get("OPENCODE_MODEL", "google/gemma-4-31b-it")
OPENCODE_CMD                 = os.environ.get(
    "OPENCODE_CMD", r"C:\nvm4w\nodejs\opencode.cmd"
)

MAX_CHAIN_DEPTH = 3
CALL_PATTERN = re.compile(r"^CALL_AGENT:\s*(\S+)\s*\|\s*(.+)$", re.MULTILINE)

# Boot-time sanity log (booleans only — never log secret values)
log.info(f"[boot] GOOGLE_GENERATIVE_AI_API_KEY set: {bool(GOOGLE_GENERATIVE_AI_API_KEY)}")
log.info(f"[boot] GITHUB_TOKEN set: {bool(GITHUB_TOKEN)}")
log.info(f"[boot] OPENCODE_MODEL = {OPENCODE_MODEL}")
log.info(f"[boot] OPENCODE_CMD   = {OPENCODE_CMD}")
log.info(f"[boot] WORK_ROOT      = {WORK_ROOT}")

app = FastAPI(title="OpenCode Orchestrator (local)")
os.makedirs(WORK_ROOT, exist_ok=True)


# ---------- Models ----------
class RunRequest(BaseModel):
    model_config = {"json_schema_extra": {"example": {
        "agent": "planner",
        "prompt": "Design a TODO API with JWT auth",
        "create_pr": True,
        "pr_title": "feat: add TODO API design",
    }}}

    agent: str
    prompt: str
    repo: Optional[str] = None
    base_branch: str = "main"
    branch_name: Optional[str] = None
    create_pr: bool = False
    pr_title: Optional[str] = None
    pr_body: str = ""
    depth: int = 0
    reuse_worktree: Optional[str] = None


class PRInfo(BaseModel):
    number: int
    url: str


class RunResponse(BaseModel):
    agent: str
    output: str
    exit_code: int
    branch: Optional[str] = None
    worktree: Optional[str] = None
    pr: Optional[PRInfo] = None
    follow_ups: list = []


# ---------- Agent runner ----------
def parse_frontmatter(content: str) -> tuple[str, dict]:
    """Strip YAML frontmatter from markdown. Returns (body, {key: value})."""
    frontmatter: dict = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()
            for line in parts[1].splitlines():
                line = line.strip()
                if ":" in line:
                    k, _, v = line.partition(":")
                    frontmatter[k.strip()] = v.strip()
    return body, frontmatter


def load_agent_md(agent: str) -> tuple[list[str], dict]:
    """Load instructions for an agent.

    Order:
        1. build.md body          — agent identity and core rules (frontmatter stripped)
        2. Files listed in AGENT.md instructions: — in the order declared

    Returns:
        instructions — list of strings, one block per file
        frontmatter  — dict parsed from build.md frontmatter only
    """
    agent_dir = AGENTS[agent]
    instructions: list[str] = []
    frontmatter: dict = {}

    # --- build.md (identity + core rules, frontmatter provides model/mode/etc.) ---
    build_path = agent_dir / "build.md"
    if build_path.exists():
        body, frontmatter = parse_frontmatter(build_path.read_text(encoding="utf-8"))
        if body:
            instructions.append(body)

    # --- AGENT.md: explicit ordered list of docs/skills to inject ---
    # Paths starting with _shared/ resolve against AGENTS_DIR (shared knowledge).
    # All other paths resolve against agent_dir.
    agent_index = agent_dir / "AGENT.md"
    if agent_index.exists():
        for line in agent_index.read_text(encoding="utf-8").splitlines():
            line = line.strip().lstrip("- ").strip()
            if not line or line.startswith("#") or line.endswith(":"):
                continue
            # Strip inline comments (e.g. "skills/foo.md — description")
            path_part = line.split(" —")[0].split(" -")[0].strip()
            if not path_part.endswith(".md"):
                continue
            if path_part.startswith("_shared/"):
                file_path = AGENTS_DIR / path_part
            else:
                file_path = agent_dir / path_part
            if file_path.exists():
                text = file_path.read_text(encoding="utf-8").strip()
                if text:
                    instructions.append(text)
            else:
                log.warning(f"[agent] {agent}/AGENT.md references missing file: {path_part}")

    return instructions, frontmatter


def write_opencode_config(worktree: str, agent: str) -> None:
    """Write opencode.json in worktree with model + agent instructions + permissions.

    API key is NOT written here — it comes from env var GOOGLE_GENERATIVE_AI_API_KEY.
    Reviewer is always embedded as an inline subagent so primary agents can call it
    without spawning a separate process.
    """
    agent_instructions, agent_fm = load_agent_md(agent)
    reviewer_instructions, reviewer_fm = load_agent_md("reviewer")

    # Per-agent model: frontmatter "model:" overrides the global default
    agent_model = agent_fm.get("model", OPENCODE_MODEL)

    cfg = {
        "$schema": "https://opencode.ai/config.json",
        "model": agent_model,
    }

    # Apply optional temperature from frontmatter
    if "temperature" in agent_fm:
        try:
            cfg["temperature"] = float(agent_fm["temperature"])
        except ValueError:
            pass

    # instructions = docs + agent.md body + skills (each as a separate block)
    if agent_instructions:
        cfg["instructions"] = agent_instructions

    # reviewer is called via CALL_AGENT: protocol — no inline agents config needed

    with open(os.path.join(worktree, "opencode.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    # Make sure opencode's transient files don't leak into commits
    gitignore_path = os.path.join(worktree, ".gitignore")
    existing = ""
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            existing = f.read()
    if "opencode.json" not in existing:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("\nopencode.json\n.agent_run.log\n")


def get_agent_mode(agent: str) -> str:
    """Read mode: field from agent's build.md frontmatter. Defaults to 'primary'."""
    build_path = AGENTS[agent] / "build.md"
    if not build_path.exists():
        return "primary"
    content = build_path.read_text(encoding="utf-8")
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                if line.strip().startswith("mode:"):
                    return line.split(":", 1)[1].strip()
    return "primary"


def run_agent_local(agent: str, prompt: str, worktree: str) -> tuple[str, int]:
    if agent not in AGENTS:
        raise HTTPException(404, f"Unknown agent: {agent}")

    write_opencode_config(worktree, agent)

    mode = get_agent_mode(agent)
    is_subagent = mode == "subagent"

    env = {
        **os.environ,
        "GOOGLE_GENERATIVE_AI_API_KEY": GOOGLE_GENERATIVE_AI_API_KEY,
        "GITHUB_TOKEN": GITHUB_TOKEN,
    }

    log.info(f"[spawn] agent={agent} mode={mode} worktree={worktree}")
    log.info(f"[opencode] ========== START: {agent} ==========")

    log_file = os.path.join(worktree, f".agent_run_{agent}.log")
    exit_file = os.path.join(worktree, f".agent_exit_{agent}")

    # Escape paths for PowerShell
    ps_log  = log_file.replace("'", "''")
    ps_exit = exit_file.replace("'", "''")
    ps_wt   = worktree.replace("'", "''")
    ps_cmd  = OPENCODE_CMD.replace("'", "''")
    ps_prompt = prompt.replace("'", "''").replace('"', '`"')

    ps_env_block = (
        f"$env:GOOGLE_GENERATIVE_AI_API_KEY='{GOOGLE_GENERATIVE_AI_API_KEY}'; "
        f"$env:GITHUB_TOKEN='{GITHUB_TOKEN}'; "
    )

    # Build opencode command:
    # - primary agents: opencode run --print-logs '<prompt>'
    # - subagents:      opencode run --print-logs --agent <name> '<prompt>'
    #   uses --agent flag so opencode loads the named agent's config (mode/permissions)
    if is_subagent:
        opencode_run = f"& '{ps_cmd}' run --print-logs --agent {agent} '{ps_prompt}'"
    else:
        opencode_run = f"& '{ps_cmd}' run --print-logs '{ps_prompt}'"

    if is_subagent:
        # Subagents run silently — no TUI window, output captured directly
        ps_script = (
            f"{ps_env_block}"
            f"Set-Location '{ps_wt}'; "
            f"{opencode_run} *> '{ps_log}'; "
            f"$ec = $LASTEXITCODE; "
            f"Set-Content -Path '{ps_exit}' -Value $ec"
        )
    else:
        # Primary agents get a visible TUI console window
        ps_script = (
            f"{ps_env_block}"
            f"Set-Location '{ps_wt}'; "
            f"Start-Transcript -Path '{ps_log}' -Append | Out-Null; "
            f"{opencode_run}; "
            f"$ec = $LASTEXITCODE; "
            f"Stop-Transcript | Out-Null; "
            f"Set-Content -Path '{ps_exit}' -Value $ec; "
            f"Write-Host ''; "
            f"Write-Host ('=== [{agent}] finished — exit code: ' + $ec + ' ===') -ForegroundColor Cyan; "
            f"Read-Host 'Press Enter to close'"
        )

    # Clear sentinels from any previous run
    if os.path.exists(exit_file):
        os.remove(exit_file)
    open(log_file, "w", encoding="utf-8").close()

    try:
        flags = 0 if is_subagent else subprocess.CREATE_NEW_CONSOLE
        proc = subprocess.Popen(
            ["powershell", "-NoExit" if not is_subagent else "-NonInteractive",
             "-Command", ps_script],
            creationflags=flags,
            env=env,
            stdout=subprocess.PIPE if is_subagent else None,
            stderr=subprocess.PIPE if is_subagent else None,
        )
    except FileNotFoundError:
        msg = f"opencode binary not found at {OPENCODE_CMD}. Set OPENCODE_CMD env var."
        log.error(msg)
        raise HTTPException(500, msg)

    # Wait for the sentinel exit-code file (written by PS after opencode finishes)
    import time
    timeout_s = 900
    start = time.monotonic()
    while not os.path.exists(exit_file) or os.path.getsize(exit_file) == 0:
        if time.monotonic() - start > timeout_s:
            log.error("[opencode] timeout waiting for exit sentinel — killing window")
            proc.kill()
            return_code = 124
            break
        time.sleep(1)
    else:
        try:
            return_code = int(open(exit_file).read().strip())
        except Exception:
            return_code = -1

    # Read captured output from the log file
    try:
        output = open(log_file, encoding="utf-8", errors="replace").read()
    except Exception:
        output = ""

    log.info(f"[opencode] ========== END: {agent} (exit={return_code}) ==========")
    return output, return_code


# ---------- Git helpers ----------
def repo_slug(repo_url: str) -> str:
    p = urlparse(repo_url)
    parts = p.path.strip("/").removesuffix(".git").split("/")
    return "__".join(parts)


def bare_repo_path(repo_url: str) -> str:
    return os.path.join(WORK_ROOT, repo_slug(repo_url), ".bare")


def authed_url(repo_url: str) -> str:
    if GITHUB_TOKEN and repo_url.startswith("https://"):
        return repo_url.replace(
            "https://", f"https://x-access-token:{GITHUB_TOKEN}@", 1
        )
    return repo_url


def git_run(args: list, **kwargs):
    """Run a git command; raise HTTPException 500 with stderr on failure."""
    # Disable Windows credential manager globally so token-in-URL is used
    full_args = ["git", "-c", "credential.helper="] + args[1:]
    result = subprocess.run(full_args, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        log.error(f"[git] failed: {' '.join(full_args)}\n{result.stderr}")
        raise HTTPException(500, f"git error: {result.stderr.strip()}")
    return result


def bare_git(bare: str, args: list):
    """Run a git command against a bare repo using --git-dir."""
    return git_run(["git", f"--git-dir={bare}", "-c", "safe.bareRepository=all"] + args)


def ensure_bare_repo(repo_url: str) -> str:
    bare = bare_repo_path(repo_url)
    if not os.path.exists(bare):
        log.info(f"[git] cloning {repo_url}")
        os.makedirs(os.path.dirname(bare), exist_ok=True)
        git_run(["git", "clone", "--bare", authed_url(repo_url), bare])
        bare_git(bare, ["remote", "set-url", "origin", authed_url(repo_url)])
    else:
        log.info(f"[git] fetching {bare}")
        bare_git(bare, ["fetch", "--prune", "origin"])
    return bare


def create_worktree(repo_url: str, base_branch: str, new_branch: str) -> str:
    bare = ensure_bare_repo(repo_url)
    wt_id = uuid.uuid4().hex[:8]
    wt_path = os.path.join(WORK_ROOT, repo_slug(repo_url), f"wt-{wt_id}")
    bare_git(bare, ["worktree", "add", "-b", new_branch, wt_path, base_branch])
    git_run(["git", "-C", wt_path, "config", "user.email", "agent@opencode.local"])
    git_run(["git", "-C", wt_path, "config", "user.name", "opencode-agent"])
    git_run(["git", "-C", wt_path, "config", "credential.helper", ""])
    git_run(["git", "-C", wt_path, "remote", "set-url", "origin", authed_url(repo_url)])
    return wt_path


def commit_and_push(worktree: str, branch: str, message: str) -> bool:
    git_run(["git", "-C", worktree, "add", "-A"])
    diff = subprocess.run(
        ["git", "-C", worktree, "diff", "--cached", "--quiet"],
        capture_output=True,
    )
    if diff.returncode == 0:
        log.info(f"[git] nothing to commit on {branch}")
        return False
    git_run(["git", "-C", worktree, "commit", "-m", message])
    git_run(["git", "-C", worktree, "push", "-u", "origin", branch])
    log.info(f"[git] pushed branch {branch}")
    return True


def remove_worktree(worktree: str):
    try:
        bare = subprocess.check_output(
            ["git", "-C", worktree, "rev-parse", "--git-common-dir"], text=True
        ).strip()
        bare_git(bare, ["worktree", "remove", "--force", worktree])
    except Exception as e:
        log.warning(f"[git] worktree cleanup failed: {e}")


# ---------- GitHub PR ----------
def parse_owner_repo(repo_url: str) -> tuple[str, str]:
    parts = urlparse(repo_url).path.strip("/").removesuffix(".git").split("/")
    return parts[0], parts[1]


def create_pull_request(repo_url, head_branch, base_branch, title, body) -> Optional[PRInfo]:
    if not GITHUB_TOKEN:
        log.warning("[pr] GITHUB_TOKEN not set")
        return None
    owner, repo = parse_owner_repo(repo_url)
    api = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    payload = json.dumps({
        "title": title, "body": body,
        "head": head_branch, "base": base_branch,
    }).encode()
    req = urllib.request.Request(api, data=payload, method="POST", headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            log.info(f"[pr] created #{data['number']} {data['html_url']}")
            return PRInfo(number=data["number"], url=data["html_url"])
    except Exception as e:
        log.error(f"[pr] failed: {e}")
        return None


def extract_follow_ups(output: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2).strip()) for m in CALL_PATTERN.finditer(output)]


# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "agents": list(AGENTS.keys()),
        "mode": "local",
        "model": OPENCODE_MODEL,
    }


@app.get("/agents")
def list_agents():
    return {"agents": list(AGENTS.keys())}


@app.post("/run", response_model=RunResponse)
def run(req: RunRequest):
    if req.depth > MAX_CHAIN_DEPTH:
        raise HTTPException(400, f"Max chain depth ({MAX_CHAIN_DEPTH}) exceeded")

    # Apply .env defaults when repo not specified
    if not req.repo and DEFAULT_REPO:
        req.repo = DEFAULT_REPO
    if req.base_branch == "main" and DEFAULT_BASE_BRANCH:
        req.base_branch = DEFAULT_BASE_BRANCH

    branch = None
    worktree = None
    owns_worktree = False

    if req.reuse_worktree:
        if not os.path.isdir(req.reuse_worktree):
            raise HTTPException(400, f"reuse_worktree path does not exist: {req.reuse_worktree!r}")
        worktree = req.reuse_worktree
        branch = subprocess.check_output(
            ["git", "-C", worktree, "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
    elif req.repo:
        branch = req.branch_name or f"agent/{req.agent}/{uuid.uuid4().hex[:8]}"
        worktree = create_worktree(req.repo, req.base_branch, branch)
        owns_worktree = True
    else:
        worktree = os.path.join(WORK_ROOT, f"empty-{uuid.uuid4().hex[:8]}")
        os.makedirs(worktree, exist_ok=True)
        owns_worktree = True

    output, exit_code = run_agent_local(req.agent, req.prompt, worktree)

    pr_info = None
    if req.repo and owns_worktree and exit_code == 0:
        pushed = commit_and_push(
            worktree, branch,
            message=req.pr_title or f"[{req.agent}] {req.prompt[:60]}",
        )
        if pushed and req.create_pr:
            pr_info = create_pull_request(
                repo_url=req.repo,
                head_branch=branch,
                base_branch=req.base_branch,
                title=req.pr_title or f"[{req.agent}] {req.prompt[:60]}",
                body=req.pr_body or f"Generated by `{req.agent}` agent.\n\nPrompt:\n> {req.prompt}",
            )
    elif exit_code != 0:
        log.warning(f"[run] agent={req.agent} exit={exit_code} — skipping commit and PR")

    follow_ups = []
    for next_agent, next_prompt in extract_follow_ups(output):
        log.info(f"[chain] {req.agent} -> {next_agent}")
        sub = run(RunRequest(
            agent=next_agent, prompt=next_prompt,
            reuse_worktree=worktree, depth=req.depth + 1,
        ))
        follow_ups.append(sub.model_dump())

    if owns_worktree and req.repo:
        commit_and_push(worktree, branch, message=f"[chained] post-{req.agent}")
        remove_worktree(worktree)

    return RunResponse(
        agent=req.agent, output=output, exit_code=exit_code,
        branch=branch, worktree=worktree, pr=pr_info,
        follow_ups=follow_ups,
    )


# ---------- Pipeline models ----------
import shutil
from dataclasses import dataclass, field, asdict
from typing import Literal

SIG_PLAN_COMPLETE = re.compile(r"^\s*PLAN_COMPLETE\s*$",          re.MULTILINE)
SIG_TESTS_WRITTEN = re.compile(r"^\s*TESTS_WRITTEN:\s*(T\d+)\s*$", re.MULTILINE)
SIG_TESTS_GREEN   = re.compile(r"^\s*TESTS_GREEN:\s*(T\d+)\s*$",   re.MULTILINE)
SIG_TESTS_RED     = re.compile(r"^\s*TESTS_RED:\s*(T\d+)\s*$",     re.MULTILINE)
SIG_CALL_AGENT    = re.compile(r"^\s*CALL_AGENT:\s*(\S+)\s*\|\s*(.+?)\s*$", re.MULTILINE)

TASK_HEADING = re.compile(r"^##\s+(T\d+):\s*(.+?)\s*$",           re.MULTILINE)
TASK_TYPE    = re.compile(r"^\s*-\s*\*\*type\*\*:\s*(\w+)",        re.MULTILINE)
TASK_DEPS    = re.compile(r"^\s*-\s*\*\*depends_on\*\*:\s*\[(.*?)\]", re.MULTILINE)


@dataclass
class Task:
    id: str
    title: str
    type: str                              # backend | frontend | fullstack
    depends_on: list = field(default_factory=list)
    status: str = "pending"               # pending | in_progress | done | failed
    attempts: int = 0
    final_result: str = ""


class PipelineRequest(BaseModel):
    model_config = {"json_schema_extra": {"example": {
        "requirement_path": "C:/Users/me/requirements/todo-api.md",
        "pr_title": "feat: implement TODO API",
        "max_retries": 3,
    }}}

    requirement_path: str                  # absolute path to requirement .md on host
    repo: Optional[str] = None             # defaults to DEFAULT_REPO
    base_branch: str = "main"
    branch_name: Optional[str] = None
    pr_title: Optional[str] = None
    pr_body: str = ""
    max_retries: int = 3


class TaskReport(BaseModel):
    id: str
    title: str
    type: str
    status: str
    attempts: int
    final_result: str


class PipelineResponse(BaseModel):
    status: str                            # complete | failed
    branch: str
    worktree: str
    tasks: list[TaskReport]
    pr: Optional[PRInfo] = None
    failed_at: Optional[str] = None


# ---------- Pipeline helpers ----------
def parse_tasks_md(tasks_md: str) -> list[Task]:
    """Parse docs/tasks.md into Task list. Expects ## T1: <title> headings."""
    content = open(tasks_md, encoding="utf-8").read()
    headings = list(TASK_HEADING.finditer(content))
    if not headings:
        raise HTTPException(500, "No task headings (## T<N>: title) found in docs/tasks.md")
    tasks: list[Task] = []
    for i, h in enumerate(headings):
        tid, title = h.group(1), h.group(2).strip()
        start = h.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        section = content[start:end]
        type_m = TASK_TYPE.search(section)
        ttype = type_m.group(1).lower() if type_m else "fullstack"
        if ttype not in ("backend", "frontend", "fullstack"):
            ttype = "fullstack"
        deps_m = TASK_DEPS.search(section)
        deps = [d.strip() for d in deps_m.group(1).split(",")] if deps_m else []
        tasks.append(Task(id=tid, title=title, type=ttype, depends_on=deps))
    log.info(f"[pipeline] parsed {len(tasks)} tasks: {[t.id for t in tasks]}")
    return tasks


def save_pipeline_state(worktree: str, tasks: list[Task], current: Optional[str] = None):
    state = {"current_task": current, "tasks": [asdict(t) for t in tasks]}
    state_path = pathlib.Path(worktree) / ".pipeline-state.json"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    gi = pathlib.Path(worktree) / ".gitignore"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if ".pipeline-state.json" not in existing:
        with gi.open("a", encoding="utf-8") as f:
            f.write("\n.pipeline-state.json\n")


def run_task_tdd(worktree: str, task: Task, max_retries: int) -> str:
    """Full RED→GREEN loop for one task. Returns 'GREEN' or failure reason."""

    # ── QC writes failing tests ───────────────────────────────────────────────
    log.info(f"[{task.id}] qc-engineer: write tests")
    out, code = run_agent_local(
        "qc-engineer",
        f"WRITE_TESTS {task.id}\n"
        f"Read docs/tasks.md for task {task.id} and write failing tests.",
        worktree,
    )
    if code != 0:
        return f"QC_WRITE_FAILED(exit={code})"
    if not SIG_TESTS_WRITTEN.search(out):
        log.warning(f"[{task.id}] qc did not emit TESTS_WRITTEN:{task.id} — continuing anyway")

    # ── RED → GREEN loop ─────────────────────────────────────────────────────
    engineers = (
        ["be-engineer"] if task.type == "backend"
        else ["fe-engineer"] if task.type == "frontend"
        else ["be-engineer", "fe-engineer"]          # fullstack: BE first, then FE
    )

    for attempt in range(1, max_retries + 1):
        task.attempts = attempt
        log.info(f"[{task.id}] attempt {attempt}/{max_retries}")

        for eng in engineers:
            # Engineer implements
            eng_out, eng_exit = run_agent_local(
                eng,
                f"IMPLEMENT {task.id}\n"
                f"Read docs/tasks.md for task {task.id} and the failing tests, "
                f"then implement the minimum code to make them pass.",
                worktree,
            )
            if eng_exit != 0:
                log.warning(f"[{task.id}] {eng} exit={eng_exit}, still running reviewer")

            # Reviewer always runs — triggered by CALL_AGENT: or as fallback
            call = SIG_CALL_AGENT.search(eng_out)
            rev_prompt = (
                call.group(2).strip()
                if call and call.group(1) == "reviewer"
                else f"Review changes for task {task.id}"
            )
            log.info(f"[{task.id}] reviewer ({'signal' if call else 'fallback'})")
            run_agent_local("reviewer", rev_prompt, worktree)

        # ── QC verifies ──────────────────────────────────────────────────────
        log.info(f"[{task.id}] qc-engineer: verify")
        qc_out, _ = run_agent_local(
            "qc-engineer",
            f"VERIFY_TESTS {task.id}\nRun all tests for task {task.id} and report GREEN or RED.",
            worktree,
        )
        if SIG_TESTS_GREEN.search(qc_out):
            log.info(f"[{task.id}] GREEN after {attempt} attempt(s)")
            return "GREEN"
        log.warning(f"[{task.id}] RED — retry {attempt}/{max_retries}")

    return "MAX_RETRIES"


def _build_pr_body(tasks: list[Task], req_path: str) -> str:
    lines = [f"## Pipeline: `{pathlib.Path(req_path).name}`\n", "### Tasks\n"]
    for t in tasks:
        icon = "✅" if t.status == "done" else "❌"
        lines.append(f"- {icon} **{t.id}** {t.title} `{t.type}` — {t.attempts} attempt(s)")
    lines.append("\n_Generated by opencode-agents pipeline._")
    return "\n".join(lines)


# ---------- Pipeline endpoint ----------
@app.post("/pipeline", response_model=PipelineResponse)
def pipeline(req: PipelineRequest):
    """
    Full TDD pipeline:
      1. planner      → reads requirement → writes docs/tasks.md → PLAN_COMPLETE
      2. per task:
           qc-engineer → writes failing tests → TESTS_WRITTEN: T<id>
           loop (max_retries):
             be/fe-engineer → implements → CALL_AGENT: reviewer (or fallback)
             reviewer       → reviews (subagent, silent)
             qc-engineer    → verifies → TESTS_GREEN / TESTS_RED: T<id>
      3. commit + push + PR (only if all tasks GREEN)
    """
    if not os.path.isfile(req.requirement_path):
        raise HTTPException(400, f"requirement_path not found: {req.requirement_path}")

    repo = req.repo or DEFAULT_REPO
    if not repo:
        raise HTTPException(400, "repo is required (or set DEFAULT_REPO in .env)")
    base_branch = req.base_branch or DEFAULT_BASE_BRANCH

    # Auto branch name from requirement filename
    if req.branch_name:
        branch = req.branch_name
    else:
        stem = re.sub(r"[^a-zA-Z0-9-]", "-", pathlib.Path(req.requirement_path).stem).strip("-")
        branch = f"feature/{stem}-{uuid.uuid4().hex[:8]}"

    worktree = create_worktree(repo, base_branch, branch)
    log.info(f"[pipeline] worktree={worktree} branch={branch}")

    # Copy requirement into worktree docs/
    docs_dir = pathlib.Path(worktree) / "docs"
    docs_dir.mkdir(exist_ok=True)
    shutil.copyfile(req.requirement_path, docs_dir / "requirement.md")

    failed_at = None
    tasks: list[Task] = []

    try:
        # ── Step 1: Planner ──────────────────────────────────────────────────
        log.info("[pipeline] planner")
        out, code = run_agent_local(
            "planner",
            "Read docs/requirement.md and produce docs/tasks.md.",
            worktree,
        )
        if code != 0 or not SIG_PLAN_COMPLETE.search(out):
            raise HTTPException(500, f"Planner failed (exit={code}) or missing PLAN_COMPLETE signal")

        tasks_md = docs_dir / "tasks.md"
        if not tasks_md.exists():
            raise HTTPException(500, "Planner did not create docs/tasks.md")

        tasks = parse_tasks_md(str(tasks_md))
        save_pipeline_state(worktree, tasks)

        # ── Step 2: Per-task TDD loop ─────────────────────────────────────────
        for task in tasks:
            task.status = "in_progress"
            save_pipeline_state(worktree, tasks, current=task.id)
            log.info(f"[pipeline] starting {task.id}: {task.title}")

            result = run_task_tdd(worktree, task, req.max_retries)
            task.final_result = result
            task.status = "done" if result == "GREEN" else "failed"
            save_pipeline_state(worktree, tasks, current=task.id)

            if task.status == "failed":
                failed_at = task.id
                log.error(f"[pipeline] {task.id} failed ({result}) — stopping")
                break

        # ── Step 3: Commit + push + PR ────────────────────────────────────────
        pushed = commit_and_push(
            worktree, branch,
            message=req.pr_title or f"feat: {pathlib.Path(req.requirement_path).stem}",
        )

        pr_info = None
        if pushed and failed_at is None:
            pr_info = create_pull_request(
                repo_url=repo, head_branch=branch, base_branch=base_branch,
                title=req.pr_title or f"feat: {pathlib.Path(req.requirement_path).stem}",
                body=req.pr_body or _build_pr_body(tasks, req.requirement_path),
            )
        elif failed_at:
            log.warning(f"[pipeline] skipping PR — failed at {failed_at}")

    finally:
        # Keep worktree for inspection on failure; remove on success
        if failed_at:
            log.info(f"[pipeline] worktree kept for inspection: {worktree}")
        else:
            remove_worktree(worktree)

    return PipelineResponse(
        status="complete" if failed_at is None else "failed",
        branch=branch,
        worktree=worktree,
        tasks=[TaskReport(**asdict(t)) for t in tasks],
        pr=pr_info if failed_at is None else None,
        failed_at=failed_at,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)