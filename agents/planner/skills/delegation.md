# Skill: Delegation (Choosing Task Type)

Each task gets a `type` field that tells the orchestrator which engineer to invoke.

## The three types

### `backend`
The task only touches:
- `src/` Python files (FastAPI routes, use cases, repos, domain)
- `tests/` Python files
- `alembic/` migrations

Invokes `be-engineer`.

### `frontend`
The task only touches:
- `src/` TypeScript/React files
- `tests/` Vitest test files

Invokes `fe-engineer`.

### `fullstack`
The task genuinely cannot be split because backend and frontend
must change together AND there are no test boundaries between them.

Invokes `be-engineer` then `fe-engineer` sequentially.

**Avoid this type when possible.** It is harder to test and harder to roll back.

## Decision procedure

```
Does the task touch ONLY backend files?
  yes → backend
  no  ↓
Does the task touch ONLY frontend files?
  yes → frontend
  no  ↓
Can it be split into one backend task + one frontend task
  with `depends_on: [<backend task id>]` on the frontend task?
  yes → split into two tasks (recommended)
  no  → fullstack
```

## Examples

| Description                                              | Type        |
| -------------------------------------------------------- | ----------- |
| Add `/users` endpoint                                    | backend     |
| Add login form component                                 | frontend    |
| Add login form that calls `/users/login`                 | split: BE then FE |
| Server-Sent Events tightly coupled to a chart component | fullstack   |
| Add Stripe webhook handler                               | backend     |
| Refactor sidebar layout                                  | frontend    |
