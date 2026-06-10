# Skill: Task Breakdown

Use this procedure to convert `docs/requirement.md` into a flat task list.

## Steps

### Step 1: Read the requirement

Read `docs/requirement.md` end-to-end before doing anything.
Identify:
- What is the user-facing outcome?
- Which surfaces are affected (API, UI, data model, infra)?
- Are there any external integrations (APIs, libraries, services)?

### Step 2: List the artifacts that must exist

Write yourself a quick mental list of:
- New endpoints / API routes
- New components / pages
- New data tables / migrations
- New domain entities / use cases

This is your raw material. Each artifact will map to 1-2 tasks.

### Step 3: Order by dependency

Backend usually comes before frontend (FE needs the API).
Data model usually comes before logic (you can't query a table that doesn't exist).

Rough default order:
1. Data model + migrations
2. Domain entities + use cases
3. API endpoints / adapters
4. Frontend components (in increasing complexity)
5. Wiring / glue (routing, state)

### Step 4: Slice each artifact

For each artifact in order, ask: "is this one task or many?"

Use the rules in `../docs/planning-principles.md`:
- One file is usually one task
- An endpoint with a use case + repo update is one task (BE owns the full slice)
- A page with N components is often N+1 tasks (components first, then page)

### Step 5: Validate

Before emitting the output, check each task:
- [ ] Does it have testable acceptance criteria?
- [ ] Are its dependencies among earlier task IDs only?
- [ ] Is its type correct? (`backend`, `frontend`, or `fullstack`)
- [ ] Could a single engineer finish this in one attempt?

If any answer is no, revise.
