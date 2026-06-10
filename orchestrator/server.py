"""
Orchestrator v3 — git worktree workflow + GitHub PR automation.

Each agent run:
  1. Ensure bare repo exists (clone once per repo)
  2. Fetch latest from origin
  3. Create a worktree on a new branch
  4. Spawn agent container with worktree mounted at /workspace
  5. Commit + push branch
  6. Create PR via GitHub API
  7. Cleanup worktree (branch stays on remote)

Request body:
{
  "agent": "be-engineer",
  "prompt": "Add /users endpoint",
  "repo": "https://github.com/me/proj.git",
  "base_branch": "main",
  "create_pr": true,
  "pr_title": "feat: add /users endpoint",
  "pr_body":  "Implemented by be-engineer agent"
}
"""
import os, re, uuid, json, logging, subprocess, urllib.request, shutil, pathlib
from dataclasses import dataclass, field, asdict
from typing import Optional, Literal
from urllib.parse import urlparse

# Load .env file from project root when available.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass  # dotenv not installed → fall back to OS env only

import docker
from docker.errors import ImageNotFound
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("orchestrator")

AGENTS = {
    "planner":      "opencode-planner:latest",
    "be-engineer":  "opencode-be-engineer:latest",
    "fe-engineer":  "opencode-fe-engineer:latest",
    "reviewer":     "opencode-reviewer:latest",
    "qc-engineer":  "opencode-qc-engineer:latest",
}

GOOGLE_GENERATIVE_AI_API_KEY = os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")        # for clone + PR API
WORK_ROOT = os.environ.get("WORK_ROOT", "/work")
DOCKER_NETWORK = os.environ.get("DOCKER_NETWORK", "")    # "" = default bridge (local dev)
DEFAULT_REPO = os.environ.get("DEFAULT_REPO", "")
DEFAULT_BASE_BRANCH = os.environ.get("DEFAULT_BASE_BRANCH", "main")
MAX_CHAIN_DEPTH = 3

CALL_PATTERN = re.compile(r"^CALL_AGENT:\s*(\S+)\s*\|\s*(.+)$", re.MULTILINE)

# Pipeline signal patterns
SIG_PLAN_COMPLETE = re.compile(r"^\s*PLAN_COMPLETE\s*$",          re.MULTILINE)
SIG_TESTS_WRITTEN = re.compile(r"^\s*TESTS_WRITTEN:\s*(T\d+)\s*$", re.MULTILINE)
SIG_TESTS_GREEN   = re.compile(r"^\s*TESTS_GREEN:\s*(T\d+)\s*$",   re.MULTILINE)
SIG_TESTS_RED     = re.compile(r"^\s*TESTS_RED:\s*(T\d+)\s*$",     re.MULTILINE)
SIG_CALL_AGENT    = re.compile(r"^\s*CALL_AGENT:\s*(\S+)\s*\|\s*(.+?)\s*$", re.MULTILINE)

TASK_HEADING = re.compile(r"^##\s+(T\d+):\s*(.+?)\s*$",           re.MULTILINE)
TASK_TYPE    = re.compile(r"^\s*-\s*\*\*type\*\*:\s*(\w+)",        re.MULTILINE)
TASK_DEPS    = re.compile(r"^\s*-\s*\*\*depends_on\*\*:\s*\[(.*)\]", re.MULTILINE)

app = FastAPI(title="OpenCode Orchestrator v3")
docker_client = docker.from_env()
os.makedirs(WORK_ROOT, exist_ok=True)


# ---------- Models ----------
class RunRequest(BaseModel):
    agent: str
    prompt: str
    repo: Optional[str] = None
    base_branch: str = "main"
    branch_name: Optional[str] = None            # auto if omitted
    create_pr: bool = False
    pr_title: Optional[str] = None
    pr_body: str = ""
    # internal
    depth: int = 0
    reuse_worktree: Optional[str] = None         # for chained agents


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


# ---------- Pipeline models ----------
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
        "requirement_path": "/requirements/todo-api.md",
        "repo": "https://github.com/me/proj.git",
        "pr_title": "feat: implement TODO API",
        "max_retries": 3,
    }}}

    requirement_path: str                  # path accessible from orchestrator container
    repo: str
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


# ---------- Git helpers ----------
def repo_slug(repo_url: str) -> str:
    """github.com/me/proj.git -> me__proj"""
    p = urlparse(repo_url)
    parts = p.path.strip("/").removesuffix(".git").split("/")
    return "__".join(parts)


def bare_repo_path(repo_url: str) -> str:
    return os.path.join(WORK_ROOT, repo_slug(repo_url), ".bare")


def authed_url(repo_url: str) -> str:
    """Inject GITHUB_TOKEN into https URL for clone/push."""
    if GITHUB_TOKEN and repo_url.startswith("https://"):
        return repo_url.replace("https://", f"https://x-access-token:{GITHUB_TOKEN}@", 1)
    return repo_url


def ensure_bare_repo(repo_url: str) -> str:
    """Clone --bare once per repo, then just fetch on subsequent calls."""
    bare = bare_repo_path(repo_url)
    if not os.path.exists(bare):
        log.info(f"[git] initial bare clone of {repo_url}")
        os.makedirs(os.path.dirname(bare), exist_ok=True)
        subprocess.run(
            ["git", "clone", "--bare", authed_url(repo_url), bare],
            check=True, capture_output=True,
        )
        # set the canonical (non-tokenized) URL for normal fetches
        subprocess.run(
            ["git", "-C", bare, "remote", "set-url", "origin", authed_url(repo_url)],
            check=True,
        )
    else:
        log.info(f"[git] fetching latest into {bare}")
        subprocess.run(
            ["git", "-C", bare, "fetch", "--prune", "origin"],
            check=True, capture_output=True,
        )
    return bare


def create_worktree(repo_url: str, base_branch: str, new_branch: str) -> str:
    bare = ensure_bare_repo(repo_url)
    wt_id = uuid.uuid4().hex[:8]
    wt_path = os.path.join(WORK_ROOT, repo_slug(repo_url), f"wt-{wt_id}")
    log.info(f"[git] worktree add {wt_path} branch={new_branch} from {base_branch}")
    subprocess.run(
        ["git", "-C", bare, "worktree", "add",
         "-b", new_branch, wt_path, base_branch],
        check=True, capture_output=True,
    )
    # configure committer in this worktree
    subprocess.run(["git", "-C", wt_path, "config", "user.email", "agent@opencode.local"], check=True)
    subprocess.run(["git", "-C", wt_path, "config", "user.name", "opencode-agent"], check=True)
    return wt_path


def commit_and_push(worktree: str, branch: str, message: str) -> bool:
    """Returns True if a push happened, False if nothing to commit."""
    subprocess.run(["git", "-C", worktree, "add", "-A"], check=True)
    diff = subprocess.run(["git", "-C", worktree, "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        log.info(f"[git] no changes on {branch}")
        return False
    subprocess.run(["git", "-C", worktree, "commit", "-m", message], check=True)
    subprocess.run(["git", "-C", worktree, "push", "-u", "origin", branch], check=True)
    log.info(f"[git] pushed {branch}")
    return True


def remove_worktree(worktree: str):
    try:
        # find bare repo from this worktree
        bare = subprocess.check_output(
            ["git", "-C", worktree, "rev-parse", "--git-common-dir"],
            text=True,
        ).strip()
        subprocess.run(
            ["git", "-C", bare, "worktree", "remove", "--force", worktree],
            check=True,
        )
        log.info(f"[git] removed worktree {worktree}")
    except Exception as e:
        log.warning(f"[git] worktree cleanup failed: {e}")


# ---------- GitHub PR ----------
def parse_owner_repo(repo_url: str) -> tuple[str, str]:
    parts = urlparse(repo_url).path.strip("/").removesuffix(".git").split("/")
    return parts[0], parts[1]


def create_pull_request(repo_url: str, head_branch: str, base_branch: str,
                        title: str, body: str) -> Optional[PRInfo]:
    if not GITHUB_TOKEN:
        log.warning("[pr] GITHUB_TOKEN not set, skipping PR creation")
        return None
    owner, repo = parse_owner_repo(repo_url)
    api = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    payload = json.dumps({
        "title": title, "body": body,
        "head": head_branch, "base": base_branch,
    }).encode()
    req = urllib.request.Request(
        api, data=payload, method="POST",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
            log.info(f"[pr] created #{data['number']} {data['html_url']}")
            return PRInfo(number=data["number"], url=data["html_url"])
    except Exception as e:
        log.error(f"[pr] failed: {e}")
        return None


# ---------- Container runner ----------
def run_agent_container(agent: str, prompt: str, worktree: str) -> tuple[str, int]:
    if agent not in AGENTS:
        raise HTTPException(404, f"Unknown agent: {agent}")
    image = AGENTS[agent]
    log.info(f"[spawn] agent={agent} wt={worktree}")
    try:
        run_kwargs = dict(
            image=image,
            environment={
                "PROMPT": prompt,
                "GOOGLE_GENERATIVE_AI_API_KEY": GOOGLE_GENERATIVE_AI_API_KEY,
                "AGENT_NAME": agent,
            },
            volumes={worktree: {"bind": "/workspace", "mode": "rw"}},
            detach=True,
        )
        if DOCKER_NETWORK:
            run_kwargs["network"] = DOCKER_NETWORK
        container = docker_client.containers.run(**run_kwargs)
        result = container.wait(timeout=900)
        logs = container.logs().decode("utf-8", errors="replace")
        container.remove(force=True)
        return logs, result.get("StatusCode", -1)
    except ImageNotFound:
        raise HTTPException(500, f"Image not built: {image}")
    except Exception as e:
        log.exception("spawn failed")
        raise HTTPException(500, f"Spawn failed: {e}")


def extract_follow_ups(output: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2).strip()) for m in CALL_PATTERN.finditer(output)]


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
    out, code = run_agent_container(
        "qc-engineer",
        f"WRITE_TESTS {task.id}\\n"
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
            eng_out, eng_exit = run_agent_container(
                eng,
                f"IMPLEMENT {task.id}\\n"
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
            run_agent_container("reviewer", rev_prompt, worktree)

        # ── QC verifies ──────────────────────────────────────────────────────
        log.info(f"[{task.id}] qc-engineer: verify")
        qc_out, _ = run_agent_container(
            "qc-engineer",
            f"VERIFY_TESTS {task.id}\\nRun all tests for task {task.id} and report GREEN or RED.",
            worktree,
        )
        if SIG_TESTS_GREEN.search(qc_out):
            log.info(f"[{task.id}] GREEN after {attempt} attempt(s)")
            return "GREEN"
        log.warning(f"[{task.id}] RED — retry {attempt}/{max_retries}")

    return "MAX_RETRIES"


def _build_pr_body(tasks: list[Task], req_path: str) -> str:
    lines = [f"## Pipeline: `{pathlib.Path(req_path).name}`\\n", "### Tasks\\n"]
    for t in tasks:
        icon = "✅" if t.status == "done" else "❌"
        lines.append(f"- {icon} **{t.id}** {t.title} `{t.type}` — {t.attempts} attempt(s)")
    lines.append("\\n_Generated by opencode-agents pipeline._")
    return "\\n".join(lines)


# ---------- Endpoints ----------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "agents": list(AGENTS.keys()),
        "mode": "docker",
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

    # --- Resolve workspace ---
    branch = None
    worktree = None
    owns_worktree = False     # only the creator cleans up

    if req.reuse_worktree:
        # Chained agent: work in the parent's worktree, same branch
        if not os.path.isdir(req.reuse_worktree):
            raise HTTPException(400, f"reuse_worktree path does not exist: {req.reuse_worktree!r}")
        worktree = req.reuse_worktree
        branch = subprocess.check_output(
            ["git", "-C", worktree, "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
        ).strip()
        log.info(f"[chain] reusing worktree {worktree} branch={branch}")
    elif req.repo:
        branch = req.branch_name or f"agent/{req.agent}/{uuid.uuid4().hex[:8]}"
        worktree = create_worktree(req.repo, req.base_branch, branch)
        owns_worktree = True
    else:
        # No repo → ephemeral empty dir (e.g. planner)
        worktree = os.path.join(WORK_ROOT, f"empty-{uuid.uuid4().hex[:8]}")
        os.makedirs(worktree, exist_ok=True)
        owns_worktree = True

    # --- Run the agent ---
    output, exit_code = run_agent_container(req.agent, req.prompt, worktree)

    # --- Commit + push + PR (only for repo-backed root runs and successful agents) ---
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

    # --- Chain follow-ups (reuse this worktree so they see the changes) ---
    follow_ups = []
    for next_agent, next_prompt in extract_follow_ups(output):
        log.info(f"[chain] {req.agent} -> {next_agent}")
        sub = run(RunRequest(
            agent=next_agent,
            prompt=next_prompt,
            reuse_worktree=worktree,
            depth=req.depth + 1,
        ))
        follow_ups.append(sub.model_dump())

    # --- Cleanup ---
    if owns_worktree and req.repo:
        # Push any additional commits from chained agents (e.g. reviewer fixes)
        commit_and_push(worktree, branch, message=f"[chained] post-{req.agent}")
        remove_worktree(worktree)

    return RunResponse(
        agent=req.agent, output=output, exit_code=exit_code,
        branch=branch, worktree=worktree, pr=pr_info,
        follow_ups=follow_ups,
    )


@app.post("/pipeline", response_model=PipelineResponse)
def pipeline(req: PipelineRequest):
    """
    Full TDD pipeline:
      1. planner      → reads requirement → writes docs/tasks.md → PLAN_COMPLETE
      2. per task:
           qc-engineer → writes failing tests → TESTS_WRITTEN: T<id>
           loop (max_retries):
             be/fe-engineer → implements → CALL_AGENT: reviewer (or fallback)
             reviewer       → reviews
             qc-engineer    → verifies → TESTS_GREEN / TESTS_RED: T<id>
      3. commit + push + PR (only if all tasks GREEN)
    """
    if not os.path.isfile(req.requirement_path):
        raise HTTPException(400, f"requirement_path not found: {req.requirement_path}")

    # Apply .env defaults
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
        out, code = run_agent_container(
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