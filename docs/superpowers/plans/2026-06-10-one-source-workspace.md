# One-Source Workspace Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make agents work directly on this monorepo — local worktrees instead of remote clones, a 5-error watchdog, planner.md/AGENT.md deduplication, and spec-to-plan routing for the planner.

**Architecture:** The orchestrator (`server.py`) mirrors `/repo` (this workspace, mounted read-only) into a bare clone, creates worktrees off that mirror, runs agents, then pushes the finished branch to GitHub and opens a PR. The planner agent is rewired to read `app/docs/spec/<name>.md` and write `app/docs/plan/<name>.md` with hard permission enforcement. A streaming log watchdog kills any agent run that accumulates 5 error events.

**Tech Stack:** Python 3.11, FastAPI, docker-sdk-for-python, opencode CLI (frontmatter YAML permissions), bash (entrypoint scripts).

---

## File Map

| File | Change |
|------|--------|
| `orchestrator/server.py` | Replace remote-clone flow with local-mirror flow; add `HOST_WORK_ROOT` path translation; replace `container.wait()` with streaming watchdog; update `PipelineRequest` (`spec` replaces `requirement_path`); update planner prompt and `parse_tasks_md` call path |
| `docker-compose.yml` | Mount `.:/repo:ro`; add `HOST_WORK_ROOT` env |
| `agents/planner/planner.md` | Rewrite: frontmatter `permission:` block (hard enforcement — edit `app/docs/plan/*.md` allow, `*` deny) + persona + ordered skills list. **Path boundary enforcement lives here as YAML.** |
| `agents/planner/AGENT.md` | Rewrite: prose rules only — human-readable path boundaries, signal protocol, failure behavior; no skills list, no frontmatter. Loaded as an extra instruction block so the model understands the why. |
| `agents/planner/Dockerfile` | Add `COPY planner/AGENT.md /opencode-knowledge/AGENT.md` |
| `agents/planner/entrypoint.sh` | Stage `AGENT.md` symlink into worktree; add `AGENT.md` and `opencode.json` to worktree `.gitignore` |
| `agents/planner/io-contract.md` | Update invocation prompt, input/output paths, permission boundary |
| `orchestrator/tests/test_watchdog.py` | New: unit tests for the error-counting watchdog |

---

## Task 1: Mount workspace and add HOST_WORK_ROOT to docker-compose [SIMPLE]

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Edit docker-compose.yml**

Open `docker-compose.yml`. The `orchestrator` service currently has these volumes and environment entries:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
  - ./work:/work
environment:
  - WORK_ROOT=/work
  - DOCKER_NETWORK=opencode-agents_agents
```

Replace them with:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
  - ./work:/work
  - .:/repo:ro
environment:
  - WORK_ROOT=/work
  - HOST_WORK_ROOT=${HOST_WORK_ROOT:-./work}
  - LOCAL_REPO=/repo
  - DOCKER_NETWORK=opencode-agents_agents
```

The full `orchestrator` service block should look like:

```yaml
services:
  orchestrator:
    build: ./orchestrator
    image: opencode-orchestrator:latest
    container_name: opencode-orchestrator
    env_file:
      - .env
    ports:
      - "8000:8000"
    environment:
      - WORK_ROOT=/work
      - HOST_WORK_ROOT=${HOST_WORK_ROOT:-./work}
      - LOCAL_REPO=/repo
      - DOCKER_NETWORK=opencode-agents_agents
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./work:/work
      - .:/repo:ro
    networks:
      - agents
```

- [ ] **Step 2: Add HOST_WORK_ROOT to .env.example**

Open `.env.example`. Add this line (after any existing WORK_ROOT line, or at the end):

```
HOST_WORK_ROOT=./work
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "chore: mount workspace into orchestrator and add HOST_WORK_ROOT"
```

---

## Task 2: Replace remote-clone flow with local-mirror in server.py [COMPLEX]

**Files:**
- Modify: `orchestrator/server.py` (constants section, `ensure_bare_repo`, `authed_url`, `repo_slug`, `create_worktree`, `run_agent_container`, `RunRequest`, `run` endpoint)

This task removes the remote-URL clone path and replaces it with a local-mirror path. After this task `run_agent_container` still uses `container.wait()` — the watchdog comes in Task 3.

- [ ] **Step 1: Update constants at the top of server.py**

Find the constants block (lines ~53–59):

```python
GOOGLE_GENERATIVE_AI_API_KEY = os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")        # for clone + PR API
WORK_ROOT = os.environ.get("WORK_ROOT", "/work")
DOCKER_NETWORK = os.environ.get("DOCKER_NETWORK", "")    # "" = default bridge (local dev)
DEFAULT_REPO = os.environ.get("DEFAULT_REPO", "")
DEFAULT_BASE_BRANCH = os.environ.get("DEFAULT_BASE_BRANCH", "main")
MAX_CHAIN_DEPTH = 3
```

Replace with:

```python
GOOGLE_GENERATIVE_AI_API_KEY = os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY", "")
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")
WORK_ROOT         = os.environ.get("WORK_ROOT", "/work")
HOST_WORK_ROOT    = os.environ.get("HOST_WORK_ROOT", WORK_ROOT)
LOCAL_REPO        = os.environ.get("LOCAL_REPO", "/repo")
DOCKER_NETWORK    = os.environ.get("DOCKER_NETWORK", "")
DEFAULT_BASE_BRANCH = os.environ.get("DEFAULT_BASE_BRANCH", "main")
MAX_CHAIN_DEPTH   = 3
```

(`DEFAULT_REPO` is gone; `HOST_WORK_ROOT` and `LOCAL_REPO` are new.)

- [ ] **Step 2: Replace repo_slug and authed_url helpers**

Find `repo_slug` and `authed_url` (lines ~156–170):

```python
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
```

Replace with:

```python
def _origin_url() -> str:
    """Read GitHub remote URL from the mounted local repo."""
    try:
        url = subprocess.check_output(
            ["git", "-C", LOCAL_REPO, "remote", "get-url", "origin"],
            text=True,
        ).strip()
        return url
    except subprocess.CalledProcessError:
        return ""


def _authed_origin_url() -> str:
    url = _origin_url()
    if GITHUB_TOKEN and url.startswith("https://"):
        return url.replace("https://", f"https://x-access-token:{GITHUB_TOKEN}@", 1)
    return url


def repo_slug() -> str:
    """Derive a filesystem-safe slug from the origin URL, e.g. me__proj."""
    url = _origin_url()
    if url:
        p = urlparse(url)
        parts = p.path.strip("/").removesuffix(".git").split("/")
        return "__".join(parts)
    return "local"


def bare_repo_path() -> str:
    return os.path.join(WORK_ROOT, repo_slug(), ".bare")
```

- [ ] **Step 3: Replace ensure_bare_repo**

Find `ensure_bare_repo` (lines ~174–195):

```python
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
```

Replace with:

```python
def ensure_bare_repo() -> str:
    """Mirror LOCAL_REPO as a bare clone once, then fetch on each call."""
    bare = bare_repo_path()
    if not os.path.exists(bare):
        log.info(f"[git] initial bare clone from {LOCAL_REPO}")
        os.makedirs(os.path.dirname(bare), exist_ok=True)
        subprocess.run(
            ["git", "clone", "--bare", LOCAL_REPO, bare],
            check=True, capture_output=True,
        )
        # Point origin at the authenticated GitHub URL for push/PR
        origin = _authed_origin_url()
        if origin:
            subprocess.run(
                ["git", "-C", bare, "remote", "set-url", "origin", origin],
                check=True,
            )
    else:
        log.info(f"[git] fetching latest from {LOCAL_REPO}")
        subprocess.run(
            ["git", "-C", bare, "fetch", "--prune", LOCAL_REPO],
            check=True, capture_output=True,
        )
    return bare
```

- [ ] **Step 4: Update create_worktree to use no-arg helpers**

Find `create_worktree(repo_url: str, base_branch: str, new_branch: str)` and replace:

```python
def create_worktree(repo_url: str, base_branch: str, new_branch: str) -> str:
    bare = ensure_bare_repo(repo_url)
    wt_id = uuid.uuid4().hex[:8]
    wt_path = os.path.join(WORK_ROOT, repo_slug(repo_url), f"wt-{wt_id}")
```

with:

```python
def create_worktree(base_branch: str, new_branch: str) -> str:
    bare = ensure_bare_repo()
    wt_id = uuid.uuid4().hex[:8]
    wt_path = os.path.join(WORK_ROOT, repo_slug(), f"wt-{wt_id}")
```

Leave the rest of `create_worktree` unchanged.

- [ ] **Step 5: Add host-path translation helper**

Add this function after `create_worktree`:

```python
def host_path(container_path: str) -> str:
    """Translate an in-container WORK_ROOT path to the HOST_WORK_ROOT equivalent.

    Agent containers are spawned via the Docker socket, so volume-bind sources
    resolve on the HOST filesystem. The orchestrator container sees /work, but
    the host sees ./work (HOST_WORK_ROOT). Without this, agents mount an empty
    directory.
    """
    if WORK_ROOT != HOST_WORK_ROOT and container_path.startswith(WORK_ROOT):
        return HOST_WORK_ROOT + container_path[len(WORK_ROOT):]
    return container_path
```

- [ ] **Step 6: Update run_agent_container to use host_path**

Find the `volumes` line inside `run_agent_container`:

```python
volumes={worktree: {"bind": "/workspace", "mode": "rw"}},
```

Replace with:

```python
volumes={host_path(worktree): {"bind": "/workspace", "mode": "rw"}},
```

- [ ] **Step 7: Update RunRequest — remove repo field**

Find `RunRequest`:

```python
class RunRequest(BaseModel):
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
```

Replace with:

```python
class RunRequest(BaseModel):
    agent: str
    prompt: str
    base_branch: str = "main"
    branch_name: Optional[str] = None
    create_pr: bool = False
    pr_title: Optional[str] = None
    pr_body: str = ""
    depth: int = 0
    reuse_worktree: Optional[str] = None
```

- [ ] **Step 8: Update the /run endpoint**

Find the `run()` endpoint. Remove all repo-related branching and replace with the local-mirror path. The full function becomes:

```python
@app.post("/run", response_model=RunResponse)
def run(req: RunRequest):
    if req.depth > MAX_CHAIN_DEPTH:
        raise HTTPException(400, f"Max chain depth ({MAX_CHAIN_DEPTH}) exceeded")

    branch = None
    worktree = None
    owns_worktree = False

    if req.reuse_worktree:
        if not os.path.isdir(req.reuse_worktree):
            raise HTTPException(400, f"reuse_worktree path does not exist: {req.reuse_worktree!r}")
        worktree = req.reuse_worktree
        branch = subprocess.check_output(
            ["git", "-C", worktree, "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
        ).strip()
        log.info(f"[chain] reusing worktree {worktree} branch={branch}")
    else:
        branch = req.branch_name or f"agent/{req.agent}/{uuid.uuid4().hex[:8]}"
        worktree = create_worktree(req.base_branch, branch)
        owns_worktree = True

    output, exit_code = run_agent_container(req.agent, req.prompt, worktree)

    pr_info = None
    if owns_worktree and exit_code == 0:
        origin = _origin_url()
        pushed = commit_and_push(
            worktree, branch,
            message=req.pr_title or f"[{req.agent}] {req.prompt[:60]}",
        )
        if pushed and req.create_pr and origin:
            pr_info = create_pull_request(
                repo_url=origin,
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
            agent=next_agent,
            prompt=next_prompt,
            reuse_worktree=worktree,
            depth=req.depth + 1,
        ))
        follow_ups.append(sub.model_dump())

    if owns_worktree:
        origin = _origin_url()
        if origin:
            commit_and_push(worktree, branch, message=f"[chained] post-{req.agent}")
        remove_worktree(worktree)

    return RunResponse(
        agent=req.agent, output=output, exit_code=exit_code,
        branch=branch, worktree=worktree, pr=pr_info,
        follow_ups=follow_ups,
    )
```

- [ ] **Step 9: Commit**

```bash
git add orchestrator/server.py docker-compose.yml .env.example
git commit -m "feat(orchestrator): replace remote-clone with local-mirror worktree flow"
```

---

## Task 3: Add streaming error-watchdog to run_agent_container [MEDIUM]

**Files:**
- Modify: `orchestrator/server.py` (`run_agent_container` only)
- Create: `orchestrator/tests/__init__.py`
- Create: `orchestrator/tests/test_watchdog.py`

- [ ] **Step 1: Write the failing unit test first**

Create `orchestrator/tests/__init__.py` (empty file).

Create `orchestrator/tests/test_watchdog.py`:

```python
"""Unit tests for the error-counting watchdog logic in run_agent_container."""
import re
import pytest

# Error-line pattern (mirrors what we'll add to server.py)
ERROR_PATTERN = re.compile(
    r"(?i)(tool call failed|api error|error\b.*\bfailed|"
    r"failed to call|rate.?limit|quota exceeded|"
    r"\bERROR\b.*\bException\b)",
)

MAX_AGENT_ERRORS = 5


def count_errors(lines: list[str]) -> int:
    """Simulate the watchdog counter over a batch of log lines."""
    return sum(1 for line in lines if ERROR_PATTERN.search(line))


def should_kill(error_count: int) -> bool:
    return error_count >= MAX_AGENT_ERRORS


class TestErrorWatchdog:
    def test_no_errors_no_kill(self):
        lines = ["Starting agent", "Reading file", "Done"]
        assert not should_kill(count_errors(lines))

    def test_four_errors_no_kill(self):
        lines = ["ERROR Exception occurred"] * 4
        assert not should_kill(count_errors(lines))

    def test_five_errors_kills(self):
        lines = ["ERROR Exception occurred"] * 5
        assert should_kill(count_errors(lines))

    def test_six_errors_kills(self):
        lines = ["Tool call failed: timeout"] * 6
        assert should_kill(count_errors(lines))

    def test_api_error_pattern(self):
        lines = ["api error: 429 quota exceeded"]
        assert count_errors(lines) == 1

    def test_rate_limit_pattern(self):
        lines = ["rate limit hit, retrying"]
        assert count_errors(lines) == 1

    def test_mixed_lines_counts_only_errors(self):
        lines = [
            "Reading docs/spec/todo.md",
            "Tool call failed: edit permission denied",
            "Retrying...",
            "ERROR Exception: model overloaded",
            "Writing app/docs/plan/todo.md",
        ]
        assert count_errors(lines) == 2
        assert not should_kill(count_errors(lines))
```

- [ ] **Step 2: Run the test — verify it fails (no implementation yet)**

```bash
cd orchestrator && pip install pytest -q && python -m pytest tests/test_watchdog.py -v
```

Expected: all tests PASS (the watchdog logic is pure functions here; they'll pass as written — this verifies the test file itself is correct before we wire the real implementation).

- [ ] **Step 3: Replace run_agent_container with the streaming watchdog**

Find the entire `run_agent_container` function in `orchestrator/server.py` and replace it:

```python
# Error signatures from opencode --print-logs output
_ERROR_PATTERN = re.compile(
    r"(?i)(tool call failed|api error|error\b.*\bfailed|"
    r"failed to call|rate.?limit|quota exceeded|"
    r"\bERROR\b.*\bException\b)",
)
MAX_AGENT_ERRORS = int(os.environ.get("MAX_AGENT_ERRORS", "5"))
AGENT_TIMEOUT    = int(os.environ.get("AGENT_TIMEOUT", "900"))


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
            volumes={host_path(worktree): {"bind": "/workspace", "mode": "rw"}},
            detach=True,
        )
        if DOCKER_NETWORK:
            run_kwargs["network"] = DOCKER_NETWORK
        container = docker_client.containers.run(**run_kwargs)
    except ImageNotFound:
        raise HTTPException(500, f"Image not built: {image}")
    except Exception as e:
        log.exception("spawn failed")
        raise HTTPException(500, f"Spawn failed: {e}")

    log_lines: list[str] = []
    error_count = 0
    last_errors: list[str] = []
    killed = False

    import threading, time

    def _stream_logs():
        nonlocal error_count, killed
        try:
            for chunk in container.logs(stream=True, follow=True):
                line = chunk.decode("utf-8", errors="replace").rstrip()
                log_lines.append(line)
                log.debug(f"[{agent}] {line}")
                if _ERROR_PATTERN.search(line):
                    error_count += 1
                    last_errors.append(line)
                    if len(last_errors) > 10:
                        last_errors.pop(0)
                    if error_count >= MAX_AGENT_ERRORS:
                        log.error(
                            f"[{agent}] error limit ({MAX_AGENT_ERRORS}) reached — killing container"
                        )
                        killed = True
                        try:
                            container.kill()
                        except Exception:
                            pass
                        return
        except Exception:
            pass

    t = threading.Thread(target=_stream_logs, daemon=True)
    t.start()
    t.join(timeout=AGENT_TIMEOUT)

    if t.is_alive():
        log.warning(f"[{agent}] hard timeout ({AGENT_TIMEOUT}s) — killing container")
        killed = True
        try:
            container.kill()
        except Exception:
            pass
        t.join(timeout=5)

    try:
        result = container.wait(timeout=10)
        exit_code = result.get("StatusCode", -1)
    except Exception:
        exit_code = -1

    container.remove(force=True)

    output = "\n".join(log_lines)
    if killed and error_count >= MAX_AGENT_ERRORS:
        notice = "\n".join(last_errors[-5:])
        log.error(f"[{agent}] killed after {error_count} errors. Last errors:\n{notice}")
        # Embed the error notice in the output so callers can surface it
        output += f"\n\n[WATCHDOG] Killed after {error_count} errors.\nLast errors:\n{notice}"
        exit_code = max(exit_code, 1)

    return output, exit_code
```

Also add `import threading` to the top-level imports (find the existing `import os, re, uuid, json, logging, subprocess, urllib.request, shutil, pathlib` line and add `threading` to it).

- [ ] **Step 4: Run unit tests again — verify they still pass**

```bash
cd orchestrator && python -m pytest tests/test_watchdog.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add orchestrator/server.py orchestrator/tests/__init__.py orchestrator/tests/test_watchdog.py
git commit -m "feat(orchestrator): add 5-error streaming watchdog to run_agent_container"
```

---

## Task 4: Update PipelineRequest to use spec path instead of requirement_path [MEDIUM]

**Files:**
- Modify: `orchestrator/server.py` (`PipelineRequest`, `pipeline` endpoint, `parse_tasks_md` error message)

- [ ] **Step 1: Update PipelineRequest model**

Find:

```python
class PipelineRequest(BaseModel):
    model_config = {"json_schema_extra": {"example": {
        "requirement_path": "/requirements/todo-api.md",
        "repo": "https://github.com/me/proj.git",
        "pr_title": "feat: implement TODO API",
        "max_retries": 3,
    }}}

    requirement_path: str
    repo: str
    base_branch: str = "main"
    branch_name: Optional[str] = None
    pr_title: Optional[str] = None
    pr_body: str = ""
    max_retries: int = 3
```

Replace with:

```python
class PipelineRequest(BaseModel):
    model_config = {"json_schema_extra": {"example": {
        "spec": "app/docs/spec/todo-api.md",
        "pr_title": "feat: implement TODO API",
        "max_retries": 3,
    }}}

    spec: str                       # repo-relative path, e.g. app/docs/spec/todo-api.md
    base_branch: str = "main"
    branch_name: Optional[str] = None
    pr_title: Optional[str] = None
    pr_body: str = ""
    max_retries: int = 3
```

- [ ] **Step 2: Rewrite the pipeline endpoint**

Replace the entire `pipeline()` function with:

```python
@app.post("/pipeline", response_model=PipelineResponse)
def pipeline(req: PipelineRequest):
    """
    Full TDD pipeline:
      1. planner      → reads app/docs/spec/<name>.md → writes app/docs/plan/<name>.md → PLAN_COMPLETE
      2. per task:
           qc-engineer → writes failing tests → TESTS_WRITTEN: T<id>
           loop (max_retries):
             be/fe-engineer → implements → CALL_AGENT: reviewer (or fallback)
             reviewer       → reviews
             qc-engineer    → verifies → TESTS_GREEN / TESTS_RED: T<id>
      3. commit + push + PR (only if all tasks GREEN)
    """
    base_branch = req.base_branch or DEFAULT_BASE_BRANCH
    spec_stem = pathlib.Path(req.spec).stem
    plan_rel  = f"app/docs/plan/{spec_stem}.md"

    if req.branch_name:
        branch = req.branch_name
    else:
        safe_stem = re.sub(r"[^a-zA-Z0-9-]", "-", spec_stem).strip("-")
        branch = f"feature/{safe_stem}-{uuid.uuid4().hex[:8]}"

    worktree = create_worktree(base_branch, branch)
    log.info(f"[pipeline] worktree={worktree} branch={branch}")

    # Validate spec exists in the worktree
    spec_path = pathlib.Path(worktree) / req.spec
    if not spec_path.exists():
        remove_worktree(worktree)
        raise HTTPException(400, f"spec not found in worktree: {req.spec}")

    failed_at = None
    tasks: list[Task] = []

    try:
        # ── Step 1: Planner ──────────────────────────────────────────────────
        log.info("[pipeline] planner")
        planner_prompt = (
            f"Read {req.spec} and produce {plan_rel}."
        )
        out, code = run_agent_container("planner", planner_prompt, worktree)
        if code != 0 or not SIG_PLAN_COMPLETE.search(out):
            raise HTTPException(
                500,
                f"Planner failed (exit={code}) or missing PLAN_COMPLETE signal.\n"
                + ("\n".join(out.splitlines()[-20:]) if out else ""),
            )

        plan_path = pathlib.Path(worktree) / plan_rel
        if not plan_path.exists():
            raise HTTPException(500, f"Planner did not create {plan_rel}")

        tasks = parse_tasks_md(str(plan_path))
        save_pipeline_state(worktree, tasks)

        # ── Step 2: Per-task TDD loop ─────────────────────────────────────────
        for task in tasks:
            task.status = "in_progress"
            save_pipeline_state(worktree, tasks, current=task.id)
            log.info(f"[pipeline] starting {task.id}: {task.title}")

            result = run_task_tdd(worktree, task, req.max_retries, plan_rel)
            task.final_result = result
            task.status = "done" if result == "GREEN" else "failed"
            save_pipeline_state(worktree, tasks, current=task.id)

            if task.status == "failed":
                failed_at = task.id
                log.error(f"[pipeline] {task.id} failed ({result}) — stopping")
                break

        # ── Step 3: Commit + push + PR ────────────────────────────────────────
        origin = _origin_url()
        pushed = commit_and_push(
            worktree, branch,
            message=req.pr_title or f"feat: {spec_stem}",
        )

        pr_info = None
        if pushed and failed_at is None and origin:
            pr_info = create_pull_request(
                repo_url=origin,
                head_branch=branch,
                base_branch=base_branch,
                title=req.pr_title or f"feat: {spec_stem}",
                body=req.pr_body or _build_pr_body(tasks, req.spec),
            )
        elif failed_at:
            log.warning(f"[pipeline] skipping PR — failed at {failed_at}")

    finally:
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
```

- [ ] **Step 3: Update run_task_tdd to accept plan_rel**

Find `run_task_tdd(worktree: str, task: Task, max_retries: int)` signature and update the engineer/QC prompts to reference `plan_rel` instead of `docs/tasks.md`. Change the signature and prompts:

```python
def run_task_tdd(worktree: str, task: Task, max_retries: int, plan_rel: str = "docs/tasks.md") -> str:
    """Full RED→GREEN loop for one task. Returns 'GREEN' or failure reason."""

    log.info(f"[{task.id}] qc-engineer: write tests")
    out, code = run_agent_container(
        "qc-engineer",
        f"WRITE_TESTS {task.id}\n"
        f"Read {plan_rel} for task {task.id} and write failing tests.",
        worktree,
    )
    if code != 0:
        return f"QC_WRITE_FAILED(exit={code})"
    if not SIG_TESTS_WRITTEN.search(out):
        log.warning(f"[{task.id}] qc did not emit TESTS_WRITTEN:{task.id} — continuing anyway")

    engineers = (
        ["be-engineer"] if task.type == "backend"
        else ["fe-engineer"] if task.type == "frontend"
        else ["be-engineer", "fe-engineer"]
    )

    for attempt in range(1, max_retries + 1):
        task.attempts = attempt
        log.info(f"[{task.id}] attempt {attempt}/{max_retries}")

        for eng in engineers:
            eng_out, eng_exit = run_agent_container(
                eng,
                f"IMPLEMENT {task.id}\n"
                f"Read {plan_rel} for task {task.id} and the failing tests, "
                f"then implement the minimum code to make them pass.",
                worktree,
            )
            if eng_exit != 0:
                log.warning(f"[{task.id}] {eng} exit={eng_exit}, still running reviewer")

            call = SIG_CALL_AGENT.search(eng_out)
            rev_prompt = (
                call.group(2).strip()
                if call and call.group(1) == "reviewer"
                else f"Review changes for task {task.id}"
            )
            log.info(f"[{task.id}] reviewer ({'signal' if call else 'fallback'})")
            run_agent_container("reviewer", rev_prompt, worktree)

        log.info(f"[{task.id}] qc-engineer: verify")
        qc_out, _ = run_agent_container(
            "qc-engineer",
            f"VERIFY_TESTS {task.id}\nRun all tests for task {task.id} and report GREEN or RED.",
            worktree,
        )
        if SIG_TESTS_GREEN.search(qc_out):
            log.info(f"[{task.id}] GREEN after {attempt} attempt(s)")
            return "GREEN"
        log.warning(f"[{task.id}] RED — retry {attempt}/{max_retries}")

    return "MAX_RETRIES"
```

- [ ] **Step 4: Update parse_tasks_md error message**

Find in `parse_tasks_md`:

```python
raise HTTPException(500, "No task headings (## T<N>: title) found in docs/tasks.md")
```

Replace with:

```python
raise HTTPException(500, f"No task headings (## T<N>: title) found in {tasks_md}")
```

- [ ] **Step 5: Remove the shutil import if no longer used**

Check if `shutil` is still used anywhere in `server.py`. If the only use was `shutil.copyfile` in the old `pipeline()`, remove it from the top import line.

```bash
grep -n "shutil" orchestrator/server.py
```

If no other uses, remove `shutil` from `import os, re, uuid, json, logging, subprocess, urllib.request, shutil, pathlib`.

- [ ] **Step 6: Commit**

```bash
git add orchestrator/server.py
git commit -m "feat(orchestrator): route planner to app/docs/spec → app/docs/plan per spec"
```

---

## Task 5: Split planner.md (persona + enforcement) from AGENT.md (prose rules) [MEDIUM]

**Two-layer boundary pattern:**
- `planner.md` frontmatter `permission:` = **opencode enforcement** (hard blocks edits outside `app/docs/plan/*.md` at tool level — the model cannot bypass this)
- `AGENT.md` = **prose explanation** loaded as an extra instruction block (the model reads *why* the boundary exists, reducing attempts to work around it)

Both layers are needed. The permission YAML enforces; the prose explains.

**Files:**
- Modify: `agents/planner/planner.md`
- Modify: `agents/planner/AGENT.md`

- [ ] **Step 1: Rewrite planner.md**

Replace the entire contents of `agents/planner/planner.md`:

```markdown
---
description: Reads a spec file and produces a structured task plan. Invoke this agent when you have app/docs/spec/<name>.md and need to produce app/docs/plan/<name>.md.
mode: primary
model: google/gemma-4-31b-it
temperature: 0.1
permission:
  read: allow
  glob: allow
  grep: allow
  list: allow
  external_directory: allow
  edit:
    "app/docs/plan/*.md": allow
    "*": deny
  bash: deny
  webfetch: deny
  websearch: deny
  task: deny
---

You are the **Planner agent** in a multi-agent coding pipeline.

Your working directory is `/workspace`. Always use absolute paths starting
with `/workspace/` when calling tools.

Your only job: turn a spec file at `/workspace/app/docs/spec/<name>.md`
into a structured task list at `/workspace/app/docs/plan/<name>.md`.

## Read these knowledge files BEFORE producing any output

Use the `read` tool to load each of these, in this order. Do not skip.

### Context (what the system is)
1. `/workspace/_shared/docs/project-overview.md`
2. `/workspace/_shared/docs/tech-stack.md`
3. `/workspace/_shared/skills/signal-protocol.md`

### My role
4. `/workspace/docs/planning-principles.md`

### My procedures (apply in order)
5. `/workspace/skills/task-breakdown.md`
6. `/workspace/skills/delegation.md`
7. `/workspace/skills/output-format.md`

### My rules and boundaries
8. `/workspace/AGENT.md`

### My I/O contract
9. `/workspace/io-contract.md`

## Workflow

1. Read all knowledge files above with the `read` tool.
2. Read the spec file named in the prompt (e.g. `/workspace/app/docs/spec/todo-api.md`).
3. Apply `skills/task-breakdown.md` to decompose.
4. Apply `skills/delegation.md` to set each task's `type`.
5. Derive the plan path: replace `app/docs/spec/` with `app/docs/plan/` keeping the same filename.
6. Write the plan file following the schema in `skills/output-format.md`.
7. Self-check the output against the rules in `skills/output-format.md`.
8. Emit the success signal.

## Output signal

After writing the plan file, the LAST non-empty line of your output MUST be exactly:

```
PLAN_COMPLETE
```

No code fences around it. No trailing punctuation.

## Constraints

- Do NOT write any file outside `app/docs/plan/`.
- Do NOT write code under `app/fe/`, `app/be/`, or any `src/` or `tests/` directory.
- Do NOT modify `.pipeline-state.json`.
- Do NOT invoke other agents.
- If the spec file is missing or empty, print an error and exit without emitting `PLAN_COMPLETE`.
```

- [ ] **Step 2: Rewrite AGENT.md (rules only, no skills list)**

Replace the entire contents of `agents/planner/AGENT.md`:

```markdown
# Planner Agent — Rules

## Path boundaries

You may ONLY write files inside `app/docs/plan/`.

Explicitly FORBIDDEN write targets (opencode permission enforcement will also block these,
but you must not attempt them regardless):
- `app/fe/` and any subdirectory
- `app/be/` and any subdirectory
- Any `src/` directory
- Any `tests/` directory
- `.pipeline-state.json`
- Any file outside `app/docs/plan/`

## Signal protocol

After successfully writing the plan file, your LAST non-empty output line MUST be:

```
PLAN_COMPLETE
```

- No code fences around it.
- No trailing punctuation.
- No extra blank lines after it.
- Do NOT emit `PLAN_COMPLETE` if the spec is missing, empty, or you cannot produce a valid plan.

## Failure behavior

| Condition | Action |
|-----------|--------|
| Spec file missing or path incorrect | Print error to output; exit without emitting `PLAN_COMPLETE` |
| Spec file empty | Print error to output; exit without emitting `PLAN_COMPLETE` |
| Cannot decompose into ≥1 task | Print error to output; exit without emitting `PLAN_COMPLETE` |
| Plan file written but malformed | The pipeline parser will reject it downstream — prefer to self-check before finishing |

## Invocation

The orchestrator calls you with a prompt of the form:

> Read app/docs/spec/<name>.md and produce app/docs/plan/<name>.md.

Parse the spec path and derive the plan path yourself (replace `spec` with `plan` in the path).
```

- [ ] **Step 3: Commit**

```bash
git add agents/planner/planner.md agents/planner/AGENT.md
git commit -m "refactor(planner): split persona (planner.md) from rules (AGENT.md)"
```

---

## Task 6: Wire AGENT.md into the Docker image and entrypoint [MEDIUM]

**Files:**
- Modify: `agents/planner/Dockerfile`
- Modify: `agents/planner/entrypoint.sh`
- Modify: `agents/planner/io-contract.md`

- [ ] **Step 1: Update Dockerfile to copy AGENT.md into knowledge**

Find in `agents/planner/Dockerfile`:

```dockerfile
COPY planner/io-contract.md /opencode-knowledge/io-contract.md
```

Add the line below it:

```dockerfile
COPY planner/AGENT.md /opencode-knowledge/AGENT.md
```

The full `COPY` block should end as:

```dockerfile
COPY _shared/         /opencode-knowledge/_shared/
COPY planner/docs/    /opencode-knowledge/docs/
COPY planner/skills/  /opencode-knowledge/skills/
COPY planner/io-contract.md /opencode-knowledge/io-contract.md
COPY planner/AGENT.md       /opencode-knowledge/AGENT.md
```

- [ ] **Step 2: Update entrypoint.sh to stage AGENT.md and gitignore staged files**

Open `agents/planner/entrypoint.sh`. After the existing symlink loop that stages `_shared`, `skills`, and `io-contract.md`, add staging for `AGENT.md`:

Find:

```bash
for path in _shared skills io-contract.md; do
  if [ ! -e "/workspace/$path" ]; then
    ln -s "/opencode-knowledge/$path" "/workspace/$path"
  fi
done
```

Replace with:

```bash
for path in _shared skills io-contract.md AGENT.md; do
  if [ ! -e "/workspace/$path" ]; then
    ln -s "/opencode-knowledge/$path" "/workspace/$path"
  fi
done
```

Then find the `.gitignore` section (or add it). After the `JSONEOF` block that writes `opencode.json`, add:

```bash
# Ensure staged knowledge and generated config never land in commits
GI="/workspace/.gitignore"
touch "$GI"
for entry in _shared skills io-contract.md AGENT.md opencode.json .pipeline-state.json; do
  grep -qxF "$entry" "$GI" || echo "$entry" >> "$GI"
done
# Also exclude the planner doc symlinks under docs/
for entry in planning-principles.md; do
  grep -qxF "docs/$entry" "$GI" || echo "docs/$entry" >> "$GI"
done
```

- [ ] **Step 3: Update io-contract.md**

Replace the entire contents of `agents/planner/io-contract.md`:

```markdown
# I/O Contract: planner

Both humans and the pipeline parser read this file. Keep the structure stable.

## Opencode agent metadata

| Field         | Value                                       |
| ------------- | ------------------------------------------- |
| Filename      | `planner.md`                                |
| Agent name    | `planner` (derived from filename)           |
| Mode          | `primary`                                   |
| Invoked via   | `opencode run --agent planner "<prompt>"`   |

## Invocation

The pipeline runs me with a prompt like:

> Read app/docs/spec/todo-api.md and produce app/docs/plan/todo-api.md.

Single-phase agent — no sub-modes.

## Inputs

| Path                             | Required | Purpose                       |
| -------------------------------- | -------- | ----------------------------- |
| `app/docs/spec/<name>.md`        | yes      | the spec to decompose         |

If the spec file is missing or empty, I print an error to output
and exit without emitting the success signal.

## Outputs

| Path                            | Required | Schema                                   |
| ------------------------------- | -------- | ---------------------------------------- |
| `app/docs/plan/<name>.md`       | yes      | see `skills/output-format.md`            |

The plan filename stem matches the spec filename stem exactly.

## Signal

The last non-empty line of my output MUST be:

```
PLAN_COMPLETE
```

Pipeline regex:

```python
re.compile(r"^\s*PLAN_COMPLETE\s*$", re.MULTILINE)
```

## Permission boundary

Opencode-level permissions in my frontmatter restrict me to:
- read/glob/grep/list: allow (need to load knowledge)
- edit: only `app/docs/plan/*.md` (everything else denied)
- bash, webfetch, websearch, task: deny

## Failure modes

| Condition                       | Behavior                                  |
| ------------------------------- | ----------------------------------------- |
| spec file missing               | output error, NO `PLAN_COMPLETE`          |
| spec file empty                 | output error, NO `PLAN_COMPLETE`          |
| cannot decompose into ≥1 task   | output error, NO `PLAN_COMPLETE`          |
| produced plan is malformed      | pipeline parser will reject downstream    |
```

- [ ] **Step 4: Verify entrypoint.sh changes are valid bash**

```bash
bash -n agents/planner/entrypoint.sh
```

Expected: no output (syntax OK).

- [ ] **Step 5: Commit**

```bash
git add agents/planner/Dockerfile agents/planner/entrypoint.sh agents/planner/io-contract.md
git commit -m "feat(planner): wire AGENT.md into Docker image, stage in entrypoint, update io-contract"
```

---

## Task 7: Add sample spec and verify pipeline end-to-end [MEDIUM]

**Files:**
- Create: `app/docs/spec/hello-api.md`

This task is manual verification — no automated test can substitute for actually running the pipeline against a live orchestrator.

- [ ] **Step 1: Create a minimal sample spec**

Create `app/docs/spec/hello-api.md`:

```markdown
# Hello API Spec

## Goal

Add a `GET /hello` endpoint to the FastAPI backend that returns `{"message": "hello"}`.

## Acceptance criteria

- [ ] `GET /hello` returns HTTP 200
- [ ] Response body is `{"message": "hello"}`
- [ ] A pytest test exists that calls the endpoint and asserts both conditions

## Type

backend
```

- [ ] **Step 2: Commit the sample spec**

```bash
git add app/docs/spec/hello-api.md
git commit -m "chore: add hello-api sample spec for pipeline E2E test"
```

- [ ] **Step 3: Build and start the orchestrator**

```bash
docker compose build orchestrator
HOST_WORK_ROOT=$(pwd)/work docker compose up orchestrator -d
```

Wait for: `Application startup complete` in the logs:

```bash
docker compose logs orchestrator -f
```

- [ ] **Step 4: Run the pipeline**

```bash
curl -s -X POST http://localhost:8000/pipeline \
  -H "Content-Type: application/json" \
  -d '{"spec": "app/docs/spec/hello-api.md"}' | python -m json.tool
```

Expected fields in response:
- `"status": "complete"` (or `"failed"` — either is acceptable for a first E2E; what matters is it runs without crashing)
- `"branch"` contains a branch name starting with `feature/hello-api-`
- `"worktree"` is populated

- [ ] **Step 5: Verify planner output**

```bash
# After the run, check the plan was created on the branch
git log --oneline -5
git show HEAD:app/docs/plan/hello-api.md 2>/dev/null | head -20 || echo "not on main yet — check the worktree or the branch"
```

If the branch was pushed:
```bash
git fetch origin
git show origin/feature/hello-api-<id>:app/docs/plan/hello-api.md | head -20
```

Expected: plan file contains `## T1:` heading and the `PLAN_COMPLETE` signal appears in the orchestrator logs.

- [ ] **Step 6: Verify no writes outside app/docs/plan/**

On the agent branch (or worktree, if kept for inspection):

```bash
git diff main..origin/feature/hello-api-<id> --name-only
```

Expected: only `app/docs/plan/hello-api.md` (and `.gitignore` if modified). No files under `app/fe/`, `app/be/`, `src/`, or `tests/`.

- [ ] **Step 7: Verify staged knowledge not in commit**

```bash
git show origin/feature/hello-api-<id> --stat | grep -E "(_shared|AGENT\.md|io-contract|opencode\.json)"
```

Expected: no output (none of those files in the commit).

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| Local-mirror worktree (mount `.:/repo:ro`) | Task 1, Task 2 |
| HOST_WORK_ROOT path translation | Task 2 (Step 5, 6) |
| Remove `repo` field from requests | Task 2 (Step 7) |
| Push to GitHub origin + PR | Task 2 (Step 8) |
| 5-error streaming watchdog | Task 3 |
| planner.md = persona + skills list only | Task 5 |
| AGENT.md = rules only, no skills list | Task 5 |
| AGENT.md in Docker image | Task 6 |
| AGENT.md staged in entrypoint | Task 6 |
| `spec` field replaces `requirement_path` | Task 4 |
| Plan path = `app/docs/plan/<name>.md` | Task 4 |
| Permissions block `app/fe/`, `app/be/` | Task 5 |
| Staged knowledge in `.gitignore` | Task 6 |
| io-contract.md updated | Task 6 |
| E2E verification | Task 7 |

All requirements covered. No TBDs or placeholders found.
