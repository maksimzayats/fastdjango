# Question Mappings

## Architecture

| Question | Read |
|----------|------|
| Why should controllers avoid ORM queries? | `docs/en/concepts/service-layer.md` |
| Where should business logic live? | `docs/en/concepts/service-layer.md` |
| How does dependency injection work? | `docs/en/concepts/ioc-container.md` |
| How are controllers structured? | `docs/en/concepts/controller-pattern.md` |
| Why use factories? | `docs/en/concepts/factory-pattern.md` |

## Implementation

| Task | Read |
|------|------|
| Add a new domain | `docs/en/how-to/add-new-domain.md` |
| Add a Celery task | `docs/en/how-to/add-celery-task.md` |
| Handle domain exceptions | `docs/en/how-to/custom-exception-handling.md` |
| Secure endpoints | `docs/en/how-to/secure-endpoints.md` |
| Override dependencies in tests | `docs/en/how-to/override-ioc-in-tests.md` |

## Setup

| Question | Read |
|----------|------|
| How do I start locally? | `docs/en/getting-started/quick-start.md` |
| What env vars exist? | `docs/en/reference/environment-variables.md` |
| What Docker services exist? | `docs/en/reference/docker-services.md` |
| What make commands exist? | `docs/en/reference/makefile.md` |

## Troubleshooting

| Symptom | Read |
|---------|------|
| Dependency is not mocked in a test | `docs/en/how-to/override-ioc-in-tests.md` |
| Endpoint exception is not mapped | `docs/en/how-to/custom-exception-handling.md` |
| Task is not available by registry property | `docs/en/how-to/add-celery-task.md` |
| Static files do not load in admin | `docs/en/reference/docker-services.md` |
