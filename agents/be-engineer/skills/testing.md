# Testing skill

- Write tests BEFORE implementation (TDD)
- Use `pytest-asyncio` with `@pytest.mark.asyncio`
- Use `httpx.AsyncClient` with `ASGITransport` for endpoint tests
- Mock external dependencies with `pytest-mock`
- Follow AAA pattern: Arrange / Act / Assert
- Minimum 80% coverage — run `pytest --cov` to verify
