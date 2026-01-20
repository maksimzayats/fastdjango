---
name: test-writer
description: Writes tests using IoC overrides and test factories.
version: 1.0.0
---

# Test Writer Skill

This skill guides you through writing tests for this codebase using the established test patterns with IoC container overrides and test factories.

## Quick Reference: Test Locations

| Test Type | Location | When to Use |
|-----------|----------|-------------|
| HTTP API integration | `tests/integration/http/<domain>/` | Testing controllers via HTTP |
| Celery task integration | `tests/integration/tasks/` | Testing background tasks |
| Unit tests | `tests/unit/<domain>/` | Testing services in isolation |

## Core Testing Patterns

### 1. Function-Scoped Container (Isolation)

Every test gets a fresh IoC container:

```python
from infrastructure.frameworks.punq import AutoRegisteringContainer
from ioc.container import ContainerFactory


@pytest.fixture(scope="function")
def container() -> AutoRegisteringContainer:
    container_factory = ContainerFactory()
    return container_factory()
```

This enables:
- Complete test isolation
- Per-test IoC overrides for mocking
- No shared state between tests

### 2. Test Factories

Available factories in `tests/integration/factories.py`:

| Factory | Creates | Usage |
|---------|---------|-------|
| `TestClientFactory` | HTTP test client | `test_client_factory(auth_for_user=user)` |
| `TestUserFactory` | Test users | `user_factory(username="test")` |
| `TestCeleryWorkerFactory` | Celery worker context | `with celery_worker_factory():` |
| `TestTasksRegistryFactory` | Task registry | `tasks_registry_factory()` |

### 3. IoC Override Pattern

**Critical**: Override BEFORE creating factories.

```python
@pytest.mark.django_db(transaction=True)
def test_with_mock(
    container: AutoRegisteringContainer,
    user_factory: TestUserFactory,
) -> None:
    # 1. Create mock
    mock_service = MagicMock(spec=SomeService)
    mock_service.some_method.return_value = expected_value

    # 2. Override BEFORE creating test client
    container.register(SomeService, instance=mock_service)

    # 3. Create test client (uses mock)
    user = user_factory()
    test_client_factory = TestClientFactory(container=container)
    with test_client_factory(auth_for_user=user) as test_client:
        # 4. Make request
        response = test_client.get("/v1/endpoint/")

    # 5. Assert
    assert response.status_code == HTTPStatus.OK
    mock_service.some_method.assert_called_once()
```

## HTTP API Test Template

```python
@pytest.mark.django_db(transaction=True)
def test_create_success(self, test_client_factory: TestClientFactory, user: User) -> None:
    with test_client_factory(auth_for_user=user) as test_client:
        response = test_client.post("/v1/<domain>s/", json={"name": "Test"})

    assert response.status_code == HTTPStatus.OK
```

Full CRUD test template: See `references/testing-new-features.md`

## Celery Task Test Template

```python
with celery_worker_factory():
    result = registry.<task_name>.delay().get(timeout=5)
assert result == expected_value
```

Full task test patterns: See `references/test-scenarios.md`

## Mocking Patterns

### Mock Return Value

```python
mock_service = MagicMock(spec=ProductService)
mock_service.get_by_id.return_value = Product(id=1, name="Test")
```

### Mock Exception

```python
mock_service = MagicMock(spec=ProductService)
mock_service.get_by_id.side_effect = ProductNotFoundError("Not found")
```

### Verify Mock Called

```python
mock_service.get_by_id.assert_called_once_with(product_id=1)
mock_service.create.assert_called_with(name="Test", price=99.99)
```

## Test Markers

| Marker | When to Use |
|--------|-------------|
| `@pytest.mark.django_db` | Any test accessing database |
| `@pytest.mark.django_db(transaction=True)` | Integration tests (required) |
| `@pytest.mark.slow` | Tests > 1 second |

## Running Tests

```bash
# All tests with coverage
make test

# Specific file
pytest tests/integration/http/<domain>/test_<domain>.py -v

# Specific class
pytest tests/integration/http/<domain>/test_<domain>.py::TestCreate<Model> -v

# With coverage report
pytest --cov=src --cov-report=html
```

## Creating a Custom Test Factory

```python
class Test<Model>Factory(ContainerBasedFactory):
    def __call__(self, user: User, name: str = "Test") -> <Model>:
        return self._container.resolve(<Domain>Service).create(user_id=user.pk, name=name)
```

Full factory + fixture pattern: See `references/testing-new-features.md`

## Common Testing Scenarios

See `references/test-scenarios.md` for:
- User-scoped resource tests
- Error handling tests
- Pagination tests
- Rate limiting tests
- Async controller tests

## Documentation

For detailed testing guidance:
- Tutorial: `docs/en/tutorial/06-testing.md`
- IoC overrides: `docs/en/how-to/override-ioc-in-tests.md`
