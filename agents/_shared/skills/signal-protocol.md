# Signal Protocol

The orchestrator parses your stdout to know what happened.
Signals are PLAIN LINES at the start or end of a line, no quotes, no code fences.

## Rules every agent follows

1. The **last non-empty line** of your output is the signal line.
2. Signals are CASE-SENSITIVE.
3. Never put signals inside code blocks (```), quotes, or markdown emphasis.
4. Never invent your own signals. Only use ones declared in your io-contract.

## Common signals

| Signal                       | Who emits                | Meaning                          |
| ---------------------------- | ------------------------ | -------------------------------- |
| `PLAN_COMPLETE`              | planner                  | tasks.md is ready                |
| `TESTS_WRITTEN: T<id>`       | qc-engineer (write)      | failing tests written for task  |
| `TESTS_GREEN: T<id>`         | qc-engineer (verify)     | all tests pass for task          |
| `TESTS_RED: T<id>`           | qc-engineer (verify)     | some tests fail for task         |
| `CALL_AGENT: <name> \| <prompt>` | be/fe-engineer (optional) | request a specific next agent |

## What happens if you forget the signal

The orchestrator raises an error and stops the pipeline.
Your last 400 chars of output get logged.
Always emit the signal — it is more important than any narrative text.

## Example (correct)

```
... your work output ...

I implemented the user model and added a migration.

CALL_AGENT: reviewer | Review the changes for T1
```

## Example (WRONG — signal inside code block)

```
Here is what I did:
\`\`\`
CALL_AGENT: reviewer | ...   ← orchestrator ignores this
\`\`\`
```
