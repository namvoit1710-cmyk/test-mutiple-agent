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
| `app/docs/plan/<name>.md`       | yes      | see `skills/writing-plans/SKILL.md`      |

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
