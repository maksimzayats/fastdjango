# Domain Checklist

Use this checklist for a new domain such as `product`.

## Core

- [ ] Create `src/fastdjango/core/product/__init__.py`.
- [ ] Create `apps.py` with `ProductConfig`.
- [ ] Add the app config to `DjangoSettings.installed_apps`.
- [ ] Create `models.py`.
- [ ] Create domain exceptions in `exceptions.py` or beside a narrow service.
- [ ] Create DTOs in `dtos.py` when use-case inputs/outputs need structured data.
- [ ] Create `use_cases.py` or `services.py`, inheriting from `BaseUseCase` or `BaseService`.

## Delivery

- [ ] Create `delivery/fastapi/schemas.py` using `BaseFastAPISchema`.
- [ ] Create `delivery/fastapi/controllers.py`.
- [ ] Create `delivery/django/admin.py` when the model needs admin support.
- [ ] Create `delivery/celery/` only when the domain owns tasks.

## Entrypoints

- [ ] Add the FastAPI controller field and router registration in `entrypoints/fastapi/factories.py`.
- [ ] For Celery tasks, define task-name constants in the domain task module.
- [ ] Add those constants to the `TaskName` enum in `entrypoints/celery/registry.py`.
- [ ] Register Celery task controllers in `entrypoints/celery/factories.py`.

## Tests

- [ ] Add FastAPI integration tests under `tests/integration/core/<domain>/delivery/fastapi/`.
- [ ] Add Celery integration tests under `tests/integration/core/<domain>/delivery/celery/` when needed.
- [ ] Add focused unit tests under `tests/unit/core/<domain>/` for reusable logic.

## Commands

```bash
make makemigrations
make migrate
make lint
make test
```
