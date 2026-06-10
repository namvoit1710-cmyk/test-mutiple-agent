# Skill: Output Format

This is the EXACT schema for `docs/tasks.md`. Deviation breaks pipeline parsing.

## Top of file

```markdown
# Tasks: <copy the title from requirement.md>

## Overview
<2-3 sentence summary of what will be built across all tasks>

---
```

## Each task block

```markdown
## T<N>: <short title>

- **type**: <backend | frontend | fullstack>
- **depends_on**: [<comma-separated task ids, or empty>]

### Description
<one paragraph explaining what to build and why>

### Acceptance criteria
- [ ] <testable criterion>
- [ ] <testable criterion>
- [ ] <testable criterion>

### Files to modify
- <relative path from repo root> (<create | edit>)
- <relative path> (<create | edit>)

---
```

## Hard rules (these break the parser if violated)

1. Task heading MUST match exactly: `## T<digit>: <title>`
   - Correct:   `## T1: Add user model`
   - Wrong:     `## Task 1: ...`, `## T1 Add user model`, `### T1: ...`

2. The metadata lines MUST appear immediately under the heading,
   in this order:
   ```
   - **type**: ...
   - **depends_on**: [...]
   ```

3. `type` must be exactly one of: `backend`, `frontend`, `fullstack`.
   Lowercase. No other values.

4. `depends_on` is a JSON-style list:
   - Empty:        `[]`
   - One:          `[T1]`
   - Multiple:     `[T1, T2]`
   - Never:        `T1`, `[T1,T2]` (missing space is fine but inconsistent),
                   `[ "T1" ]` (no quotes)

5. Task IDs are sequential: `T1`, `T2`, `T3` ... No gaps. No reordering.

6. Tasks are separated by `---` on its own line.

## Signal

The last line of your stdout, after writing the file, MUST be:

```
PLAN_COMPLETE
```

No other text after it. No code fences around it.
