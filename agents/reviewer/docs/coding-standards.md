# Coding Standards

These standards apply to all agents.

## General

- No hardcoded secrets, API keys, or passwords
- All user inputs must be validated at system boundaries
- Error messages must not leak internal stack traces or sensitive data
- Functions must be under 50 lines; files under 300 lines
- No commented-out code

## Git

- Commit messages follow conventional commits: `feat:`, `fix:`, `refactor:`, `test:`, `chore:`
- One logical change per commit
- Never commit generated files, build artifacts, or `.env` files

## Testing

- Minimum 80% test coverage
- Tests follow AAA pattern: Arrange / Act / Assert
- Test names describe the behavior: `returns empty array when no items found`
- Every new function needs at least one happy-path and one error-path test
