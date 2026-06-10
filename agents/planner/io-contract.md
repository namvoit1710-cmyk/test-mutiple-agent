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

> Read docs/requirement.md and produce docs/tasks.md.

Single-phase agent — no sub-modes.

## Inputs

| Path                    | Required | Purpose                       |
| ----------------------- | -------- | ----------------------------- |
| `docs/requirement.md`   | yes      | the user's requirement        |

If `docs/requirement.md` is missing or empty, I print an error to stderr
and exit non-zero. I do NOT emit the success signal in that case.

## Outputs

| Path             | Required | Schema                                   |
| ---------------- | -------- | ---------------------------------------- |
| `docs/tasks.md`  | yes      | see `skills/output-format.md`            |

## Signal

The last non-empty line of my stdout MUST be:

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
- edit: only `docs/tasks.md` (everything else denied)
- bash, webfetch, websearch, task: deny

This is enforced by opencode regardless of my prompt body.

## Failure modes

| Condition                       | Behavior                                  |
| ------------------------------- | ----------------------------------------- |
| requirement.md missing          | stderr error, exit 1, NO `PLAN_COMPLETE`  |
| requirement.md empty            | stderr error, exit 1, NO `PLAN_COMPLETE`  |
| cannot decompose into ≥1 task   | stderr error, exit 1, NO `PLAN_COMPLETE`  |
| produced tasks.md is malformed  | pipeline parser will reject downstream    |