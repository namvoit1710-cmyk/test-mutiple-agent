# Design: One-Source Workspace Pipeline

**Date:** 2026-06-10
**Status:** Approved

## Overview

The agents and the target app now live in one repo (this workspace). Four behavior
changes follow from that:

1. The orchestrator creates git worktrees from this workspace instead of cloning
   a remote GitHub URL.
2. The planner's `planner.md` and `AGENT.md` stop duplicating content: `planner.md`
   is the persona (who the agent is, what it does, which skills it reads);
   `AGENT.md` is rules and instructions only, with no skills list.
3. opencode error loops are capped: after 5 errors in one agent run, the
   orchestrator kills the run and reports the error. No infinite looping.
4. The planner reads specs from `app/docs/spec/` and writes plans to
   `app/docs/plan/` — one plan file per spec. It never implements anything
   inside `app/fe/` or `app/be/`.

Scope: `orchestrator/server.py` (Docker mode) and the planner agent only.
`orchestrator/local_server.py` is untouched. The other four agents keep their
current files; the planner.md/AGENT.md split pattern rolls out to them later.

## 1. One-Source Worktree Flow (`orchestrator/server.py`)

### Current behavior

`ensure_bare_repo()` clones a remote URL (`repo` request field / `DEFAULT_REPO`)
into `/work/<slug>/.bare`, worktrees are created off that bare clone, and the
branch is pushed back to GitHub with an optional PR.

### New behavior

- `docker-compose.yml` mounts this workspace read-only into the orchestrator
  container: `.:/repo:ro`. A new env var `LOCAL_REPO` (default `/repo`) points
  at it.
- `ensure_bare_repo()` becomes a **local mirror**: first run clones `LOCAL_REPO`
  into `/work/<slug>/.bare`; later runs `git fetch` from `LOCAL_REPO`. The
  worktree code on top of the mirror is unchanged.
- Task start: `git worktree add -b <branch> /work/.../wt-<id> <base_branch>`
  where `<base_branch>` defaults to `main` — this workspace's `main` as of the
  latest fetch.
- Task done: commit on the agent branch, then **push the branch to the GitHub
  origin** and **create a PR** (existing PR code). The origin URL is read once
  from the mounted repo via `git -C /repo remote get-url origin` and authed
  with `GITHUB_TOKEN`. The mirror itself is never pushed to and `/repo` is
  never written.
- The `repo` field is removed from `RunRequest` and `PipelineRequest`; there is
  only one source. `DEFAULT_REPO` and `authed_url()`-based cloning go away;
  `repo_slug()` and the PR helpers keep working off the origin URL.

### Host-path translation (bug fix)

The orchestrator spawns agent containers through the Docker socket, so volume
bind sources resolve on the **host**, not inside the orchestrator container.
Binding `/work/wt-x` therefore fails on a Windows host. Add env var
`HOST_WORK_ROOT` (the host path of `./work`, set in `docker-compose.yml`) and
translate `WORK_ROOT`-prefixed paths to `HOST_WORK_ROOT` when mounting a
worktree into an agent container. Without this, agents see an empty workspace.

## 2. `planner.md` / `AGENT.md` Split

### Current behavior

Both files list the same knowledge files (shared docs, role doc, three skills,
io-contract). In Docker mode `AGENT.md` is not even copied into the image —
it is dead weight.

### New behavior

| File | Contains | Does NOT contain |
|------|----------|------------------|
| `planner.md` | opencode frontmatter (model, mode, temperature, permissions); persona — who I am, my job, my workflow; the **ordered skills/knowledge reading list** (the only place skills are listed) | rules that belong to AGENT.md |
| `AGENT.md` | rules and instructions only: path boundaries (edit `app/docs/plan/` only; never `app/fe/`, `app/be/`, `src/`, `tests/`), signal-protocol rules (`PLAN_COMPLETE` formatting), failure behavior (missing/empty spec → error, no signal) | any skills or knowledge-file list |

### Docker wiring

- `agents/planner/Dockerfile` copies `AGENT.md` into `/opencode-knowledge/`.
- `agents/planner/entrypoint.sh` stages it into the worktree alongside the
  other knowledge symlinks.
- The generated `/workspace/opencode.json` gains
  `"instructions": ["AGENT.md"]` so opencode loads the rules automatically.

## 3. Error-Loop Watchdog: 5 Strikes Then Stop

- `run_agent_container()` replaces blind `container.wait(timeout=900)` with
  **live log streaming** (`container.logs(stream=True)` consumed while a
  timer enforces the same 900s hard cap).
- Lines matching error signatures from opencode `--print-logs` output (tool
  call failures, provider/API errors, `ERROR`-level log lines) increment an
  error counter. At `MAX_AGENT_ERRORS` (default **5**, env-overridable) the
  orchestrator kills the container and marks the run failed.
- The failure surfaces as the "notice": the last error lines are included in
  the run/pipeline response (`final_result` for tasks, HTTP 500 detail for the
  planner stage). On failure the worktree is kept for inspection, as today.
- The 900s timeout remains the backstop for hangs that produce no error lines.

## 4. Planner Reads Spec, Writes Plan, Never Implements

### Pipeline contract

- `PipelineRequest.requirement_path` (an orchestrator-local file that was
  copied into the worktree) is replaced by **`spec`**: a repo-relative path,
  e.g. `app/docs/spec/todo-api.md`. The orchestrator validates it exists in
  the worktree; there is no copy step.
- Planner prompt: `Read app/docs/spec/<name>.md and produce
  app/docs/plan/<name>.md.` — **one plan per spec**, same filename stem.
- The plan keeps the existing task schema (`## T1: <title>`, `**type**`,
  `**depends_on**`) so `parse_tasks_md()` works unchanged, pointed at
  `app/docs/plan/<name>.md`.
- Engineer/QC prompts in the TDD loop reference the plan path instead of
  `docs/tasks.md`. (Engineer permission boundaries for `app/be/`/`app/fe/`
  are a separate later task.)

### Enforcement

`planner.md` frontmatter permissions become:

```yaml
edit:
  "app/docs/plan/*.md": allow
  "*": deny
```

opencode itself blocks any write outside `app/docs/plan/`, regardless of what
the model attempts. `bash`, `webfetch`, `websearch`, `task` stay denied.

### Knowledge staging hygiene

The worktree is now the real monorepo, so staged knowledge must never reach a
commit. The orchestrator appends the staged paths to the worktree `.gitignore`
(same mechanism as `.pipeline-state.json` today): `_shared`, `skills`,
`io-contract.md`, `AGENT.md` (the staged copy), `opencode.json`, and the
planner-doc symlinks placed under `docs/`.

### io-contract.md

Updated to match: invocation prompt, input `app/docs/spec/<name>.md`, output
`app/docs/plan/<name>.md`, unchanged `PLAN_COMPLETE` signal, new permission
boundary.

## Testing

- **Watchdog unit test:** feed canned log streams (0, 4, 5, 6 error lines)
  into the error counter; assert kill triggers exactly at 5 and the reported
  error excerpt matches the last error lines.
- **Manual watchdog test:** force a bad model name so opencode error-loops;
  verify the container dies at error #5 and the response carries the error.
- **E2E:** place a small sample spec in `app/docs/spec/`, `POST /pipeline`,
  verify: worktree branched off local `main`; `app/docs/plan/<name>.md`
  created; no writes outside `app/docs/plan/`; staged knowledge absent from
  the commit; branch pushed to origin; PR opened.

## Out of Scope

- `orchestrator/local_server.py`
- AGENT.md/persona split for be-engineer, fe-engineer, reviewer, qc-engineer
- Engineer/QC permission boundaries for `app/be/` and `app/fe/`
