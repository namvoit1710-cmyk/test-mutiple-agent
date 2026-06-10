# FastAPI skill

- Use `APIRouter` with prefix and tags for each domain
- Always use async def for route handlers
- Use Pydantic v2 models for request/response validation
- Return typed responses — never return raw dicts
- Use `HTTPException` with specific status codes and detail messages
- Add `response_model=` to every route decorator
