# Planning Principles

These principles guide how you decompose a requirement into tasks.

## 1. Sequential, not parallel

The pipeline executes tasks one at a time. Order them so each task only
depends on earlier ones. Use `depends_on` honestly — it documents intent,
not parallelism.

## 2. Small enough to test

Each task must be completable by ONE engineer in ONE attempt
(target: under 1 hour of work, under 200 lines of diff).
If a task feels bigger, split it.

Signs a task is too big:
- More than 3 files to create/modify
- More than 5 acceptance criteria
- Crosses backend and frontend (use `fullstack` only when truly inseparable;
  prefer splitting into a backend task and a frontend task with a dependency)

## 3. Testable acceptance criteria

Every criterion must be something a QC engineer can write a test for.

Good:
- [ ] GET /users returns 200 with a JSON array
- [ ] Submitting the login form with valid creds calls onLoginSuccess

Bad (vague):
- [ ] The API should work well
- [ ] UI looks good

## 4. State files to modify, but don't enumerate every file

Help the engineer find the area. Don't try to specify every helper module.

## 5. Don't write code, don't write tests

You produce a PLAN only. The QC engineer writes tests. The engineers write code.

## 6. No assumptions about the codebase

If the requirement mentions an existing feature, do NOT guess its file layout.
Describe what needs to change in plain language; the engineer will navigate.
