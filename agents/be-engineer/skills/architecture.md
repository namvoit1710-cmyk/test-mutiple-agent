# Clean Architecture skill

Layer order (dependency direction: inward only):
1. domain/       — entities, value objects, no framework imports
2. application/  — use cases, interfaces (ports)
3. adapters/     — repositories, external service clients
4. frameworks/   — FastAPI routers, SQLAlchemy models, DI wiring

Rules:
- Domain layer must have zero external dependencies
- Use cases depend only on interfaces, not concrete implementations
- Inject dependencies via constructor, never import directly across layers
