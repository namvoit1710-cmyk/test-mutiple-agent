# Review checklist skill

For every review, check in this order:

1. **Security** — see security skill
2. **Correctness** — does the code do what the task asked?
3. **Error handling** — are all failure paths handled explicitly?
4. **Types** — are types correct and non-any?
5. **Tests** — do tests exist and cover the happy path + at least one error path?
6. **Naming** — are names clear without needing a comment?
7. **Size** — functions > 50 lines or files > 300 lines should be flagged

End with either:
- `REVIEW: APPROVED`
- `REVIEW: NEEDS CHANGES` followed by a numbered list of required fixes
