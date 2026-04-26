---
name: feature-developer
description: Implements new features, domains, and API endpoints.
version: 1.0.0
---

# Feature Developer Skill

Use this skill when adding or changing application features.

## Golden Rule

```
Controller -> Use Case / Service -> Model
```

- Controllers handle FastAPI, Django admin, or Celery delivery.
- Use cases and services own ORM access and application behavior.
- Models define database structure.

## Current File Locations

| Component | Location |
|-----------|----------|
| Domain app | `src/fastdjango/core/<domain>/` |
| Model | `src/fastdjango/core/<domain>/models.py` |
| DTOs | `src/fastdjango/core/<domain>/dtos.py` |
| Use case/service | `src/fastdjango/core/<domain>/use_cases.py` or `services.py` |
| FastAPI delivery | `src/fastdjango/core/<domain>/delivery/fastapi/` |
| Django admin delivery | `src/fastdjango/core/<domain>/delivery/django/admin.py` |
| Celery delivery | `src/fastdjango/core/<domain>/delivery/celery/` |
| FastAPI composition | `src/fastdjango/entrypoints/fastapi/factories.py` |
| Celery composition | `src/fastdjango/entrypoints/celery/` |

## Workflow

1. Create or update the domain in `src/fastdjango/core/<domain>/`.
2. Put ORM logic in a use case or service inheriting from `BaseUseCase` or `BaseService`.
3. Put request/response schemas in the relevant delivery folder.
4. Add FastAPI or Celery controllers in the domain-owned delivery folder.
5. Update the relevant entrypoint factory or registry.
6. Add migrations when models change.
7. Add focused tests for user-facing behavior and reusable logic.

## Dependency Injection

This project uses `diwire` recursive auto-wiring. Most services, use cases,
controllers, and factories do not need manual registration. Add explicit
registration only when mapping an abstraction or overriding a dependency in tests.

## Verification

```bash
make format
make lint
make test
```

## References

- `docs/en/how-to/add-new-domain.md`
- `docs/en/how-to/add-celery-task.md`
- `docs/en/concepts/service-layer.md`
- `docs/en/concepts/controller-pattern.md`
- `docs/en/concepts/ioc-container.md`
- `references/domain-checklist.md`
- `references/controller-patterns.md`
- `references/testing-new-features.md`
