---
name: test-writer
description: Writes tests using IoC overrides and test factories.
version: 1.0.0
---

# Test Writer Skill

Use this skill to write focused tests for the current project structure.

## Test Locations

| Test Type | Location |
|-----------|----------|
| FastAPI integration | `tests/integration/core/<domain>/delivery/fastapi/` |
| Celery integration | `tests/integration/core/<domain>/delivery/celery/` |
| Core unit tests | `tests/unit/core/<domain>/...` |
| Infrastructure unit tests | `tests/unit/infrastructure/<adapter>/...` |

## Available Factories

Base test factory classes live in `tests/foundation/factories.py`.

- `TestClientFactory`
- `TestUserFactory`
- `TestCeleryWorkerFactory`
- `TestTasksRegistryFactory`

## IoC Override Pattern

```python
mock_service = MagicMock(spec=SomeService)
container.add_instance(mock_service, provides=SomeService)

test_client_factory = TestClientFactory(container=container)
```

Create overrides before resolving the target factory or controller.

## HTTP Test Pattern

```python
@pytest.mark.django_db(transaction=True)
def test_endpoint(
    test_client_factory: TestClientFactory,
    user: User,
) -> None:
    with test_client_factory(auth_for_user=user) as client:
        response = client.get("/v1/users/me")

    assert response.status_code == HTTPStatus.OK
```

## Celery Test Pattern

```python
registry = tasks_registry_factory()

with celery_worker_factory():
    result = registry.ping.delay().get(timeout=10)

assert result == {"result": "pong"}
```

## Commands

```bash
make test
uv run pytest tests/integration/core/user/delivery/fastapi/test_controllers.py
uv run pytest tests/integration/core/health/delivery/celery/test_tasks.py
```

Detailed references:
- `references/mock-patterns.md`
- `references/test-scenarios.md`
- `docs/en/tutorial/06-testing.md`
- `docs/en/how-to/override-ioc-in-tests.md`
