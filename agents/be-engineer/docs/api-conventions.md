# API Conventions

All API endpoints must follow these conventions.

## Response envelope

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": { "total": 0, "page": 1, "limit": 20 }
}
```

- `success` — boolean, always present
- `data` — payload, null on error
- `error` — string message, null on success
- `meta` — only present on paginated responses

## HTTP status codes

- `200` — success
- `201` — resource created
- `400` — validation error (bad request)
- `401` — unauthenticated
- `403` — unauthorized
- `404` — not found
- `422` — unprocessable entity (business rule violation)
- `500` — internal server error

## Naming

- Endpoints: lowercase kebab-case, plural nouns: `/api/v1/todo-items`
- Query params: snake_case: `?page_size=20`
- JSON fields: camelCase in responses, snake_case in Python models
