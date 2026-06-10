# Test Strategy

- Write tests before implementation (TDD — RED first)
- Each task must have at least: one happy path + one error path test
- Use pytest for Python, Jest/Vitest for TypeScript
- Test file naming: `test_<module>.py` or `<module>.test.ts`
- Tests must be independent — no shared state between tests
- Use fixtures for setup, not global variables
