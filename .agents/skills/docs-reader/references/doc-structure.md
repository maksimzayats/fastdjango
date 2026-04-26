# Documentation Structure

## Main Docs

```
docs/en/
├── index.md
├── getting-started/
│   ├── quick-start.md
│   ├── project-structure.md
│   └── development-environment.md
├── tutorial/
│   ├── 01-model-and-service.md
│   ├── 02-ioc-registration.md
│   ├── 03-http-api.md
│   ├── 04-celery-tasks.md
│   ├── 05-observability.md
│   └── 06-testing.md
├── concepts/
│   ├── service-layer.md
│   ├── ioc-container.md
│   ├── controller-pattern.md
│   ├── factory-pattern.md
│   └── pydantic-settings.md
├── how-to/
│   ├── add-new-domain.md
│   ├── add-celery-task.md
│   ├── custom-exception-handling.md
│   ├── override-ioc-in-tests.md
│   ├── secure-endpoints.md
│   └── configure-observability.md
└── reference/
    ├── environment-variables.md
    ├── makefile.md
    └── docker-services.md
```

## Code Layout The Docs Describe

```
src/fastdjango/
├── core/                 # Domain apps, models, use cases, services, delivery
├── foundation/           # Base classes and shared contracts
├── infrastructure/       # Django, logging, telemetry, throttling
├── entrypoints/          # FastAPI, Celery, Django composition roots
└── ioc/                  # diwire container setup
```

## Key Cross-References

| Topic | Primary Page |
|-------|--------------|
| Controller boundary | `docs/en/concepts/service-layer.md` |
| Dependency injection | `docs/en/concepts/ioc-container.md` |
| HTTP and Celery controllers | `docs/en/concepts/controller-pattern.md` |
| Factories | `docs/en/concepts/factory-pattern.md` |
| Settings | `docs/en/concepts/pydantic-settings.md` |
| Adding features | `docs/en/how-to/add-new-domain.md` |
| Testing | `docs/en/tutorial/06-testing.md` |
