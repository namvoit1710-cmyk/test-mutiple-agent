# Project Overview

You are an agent in a multi-agent coding pipeline. The pipeline coordinates
several specialist agents to take a requirement document and turn it into
working code on a feature branch with a pull request.

## Agents in the system

| Agent          | Role                                                |
| -------------- | --------------------------------------------------- |
| `planner`      | Breaks a requirement into sequential tasks          |
| `qc-engineer`  | Writes failing tests, then verifies they pass       |
| `be-engineer`  | Implements backend code (FastAPI, Clean Architecture)|
| `fe-engineer`  | Implements frontend code (React + TypeScript)       |
| `reviewer`     | Reviews code changes against acceptance criteria    |

## Workflow at a glance

```
requirement.md
     │
     ▼
  planner ──→ tasks.md
     │
     ▼
  for each task:
     qc-engineer (write RED tests)
        │
        ▼
     ┌──── retry loop ────┐
     │   be/fe-engineer   │
     │        │           │
     │     reviewer       │
     │        │           │
     │   qc-engineer      │
     │   (verify GREEN)   │
     └────────────────────┘
     │
     ▼
  commit + push + PR
```

## Filesystem you operate in

A git worktree on a feature branch. You can read and write any file.
Convention:

- `docs/requirement.md` — user's original requirement (input)
- `docs/tasks.md` — task list (produced by planner)
- `src/` — application code
- `tests/` — test code
- `.pipeline-state.json` — orchestrator state (DO NOT touch)

## Communication between agents

Agents do not call each other directly. They communicate by:

1. **Writing files** (e.g. planner writes `docs/tasks.md`)
2. **Emitting signal lines** in stdout (see `_shared/skills/signal-protocol.md`)

The orchestrator reads stdout, parses signals, and decides what to run next.
