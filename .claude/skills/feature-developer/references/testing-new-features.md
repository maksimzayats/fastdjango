# Testing New Features Reference

This reference provides patterns for testing new domains following the established test architecture.

## Contents

- [Test File Structure](#test-file-structure)
- [Creating a Test Factory](#creating-a-test-factory)
- [Registering the Factory Fixture](#registering-the-factory-fixture)
- [HTTP API Test Patterns](#http-api-test-patterns)
- [IoC Override Pattern for Mocking](#ioc-override-pattern-for-mocking)
- [Celery Task Test Pattern](#celery-task-test-pattern)
- [Test Markers Reference](#test-markers-reference)
- [Running Tests](#running-tests)

## Test File Structure

```
tests/
├── integration/
│   ├── factories.py              # Test factories
│   ├── conftest.py               # Shared fixtures
│   ├── http/
│   │   └── <domain>/
│   │       ├── __init__.py
│   │       └── test_<domain>.py  # HTTP API tests
│   └── tasks/
│       └── test_<task>.py        # Celery task tests
└── unit/
    └── <domain>/
        └── test_services.py      # Unit tests for services
```

## Creating a Test Factory

Add to `tests/integration/factories.py`:

```python
from core.<domain>.models import <Model>
from core.<domain>.services import <Domain>Service


class Test<Model>Factory(ContainerBasedFactory):
    """Factory for creating test <Model> instances."""

    def __call__(
        self,
        # Required parameters (no defaults)
        user: User,
        # Optional parameters (with defaults)
        name: str = "Test <Model>",
        description: str = "Test description",
        **kwargs: Any,
    ) -> <Model>:
        <domain>_service = self._container.resolve(<Domain>Service)

        return <domain>_service.create(
            name=name,
            description=description,
            user_id=user.pk,
            **kwargs,
        )
```

## Registering the Factory Fixture

Add to `tests/integration/conftest.py`:

```python
from infrastructure.frameworks.punq import AutoRegisteringContainer
from tests.integration.factories import Test < Model > Factory


@pytest.fixture(scope="function")
def <model > _factory(
    transactional_db: None

,
container: AutoRegisteringContainer,
) -> Test < Model > Factory:
return Test < Model > Factory(container=container)
```

## HTTP API Test Patterns

### Test File Template

```python
# tests/integration/http/<domain>/test_<domain>.py
from http import HTTPStatus

import pytest

from core.<domain>.models import <Model>
from core.user.models import User
from tests.integration.factories import (
    TestClientFactory,
    Test<Model>Factory,
    TestUserFactory,
)


@pytest.fixture(scope="function")
def user(user_factory: TestUserFactory) -> User:
    return user_factory(username="<domain>_test_user")


@pytest.fixture(scope="function")
def <model>(
    <model>_factory: Test<Model>Factory,
    user: User,
) -> <Model>:
    return <model>_factory(user=user, name="Existing <Model>")


class TestCreate<Model>:
    @pytest.mark.django_db(transaction=True)
    def test_create_success(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        with test_client_factory(auth_for_user=user) as test_client:
            response = test_client.post(
                "/v1/<domain>s/",
                json={
                    "name": "New <Model>",
                    "description": "Test description",
                },
            )

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == "New <Model>"
        assert "id" in data

    @pytest.mark.django_db(transaction=True)
    def test_create_requires_authentication(
        self,
        test_client_factory: TestClientFactory,
    ) -> None:
        with test_client_factory() as test_client:  # No auth
            response = test_client.post(
                "/v1/<domain>s/",
                json={"name": "Test"},
            )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.django_db(transaction=True)
    def test_create_validation_error(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        with test_client_factory(auth_for_user=user) as test_client:
            response = test_client.post(
                "/v1/<domain>s/",
                json={},  # Missing required fields
            )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class TestList<Model>s:
    @pytest.mark.django_db(transaction=True)
    def test_list_returns_user_items(
        self,
        test_client_factory: TestClientFactory,
        user: User,
        <model>: <Model>,
    ) -> None:
        with test_client_factory(auth_for_user=user) as test_client:
            response = test_client.get("/v1/<domain>s/")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert len(data) >= 1

    @pytest.mark.django_db(transaction=True)
    def test_list_empty(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        with test_client_factory(auth_for_user=user) as test_client:
            response = test_client.get("/v1/<domain>s/")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data == [] or data.get("items") == []


class TestGet<Model>:
    @pytest.mark.django_db(transaction=True)
    def test_get_success(
        self,
        test_client_factory: TestClientFactory,
        user: User,
        <model>: <Model>,
    ) -> None:
        with test_client_factory(auth_for_user=user) as test_client:
            response = test_client.get(f"/v1/<domain>s/{<model>.id}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == <model>.id

    @pytest.mark.django_db(transaction=True)
    def test_get_not_found(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        with test_client_factory(auth_for_user=user) as test_client:
            response = test_client.get("/v1/<domain>s/99999")

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestUpdate<Model>:
    @pytest.mark.django_db(transaction=True)
    def test_update_success(
        self,
        test_client_factory: TestClientFactory,
        user: User,
        <model>: <Model>,
    ) -> None:
        with test_client_factory(auth_for_user=user) as test_client:
            response = test_client.patch(
                f"/v1/<domain>s/{<model>.id}",
                json={"name": "Updated Name"},
            )

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["name"] == "Updated Name"


class TestDelete<Model>:
    @pytest.mark.django_db(transaction=True)
    def test_delete_success(
        self,
        test_client_factory: TestClientFactory,
        user: User,
        <model>: <Model>,
    ) -> None:
        with test_client_factory(auth_for_user=user) as test_client:
            response = test_client.delete(f"/v1/<domain>s/{<model>.id}")

            # Verify deletion
            verify_response = test_client.get(f"/v1/<domain>s/{<model>.id}")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert verify_response.status_code == HTTPStatus.NOT_FOUND
```

## IoC Override Pattern for Mocking

When you need to mock a service:

```python
from unittest.mock import MagicMock

import pytest

from core. < domain >.services
import < Domain > Service, < Domain > NotFoundError
from infrastructure.frameworks.punq import AutoRegisteringContainer


class TestWithMockedService:
    @pytest.mark.django_db(transaction=True)
    def test_handles_service_error(
            self,
            container: AutoRegisteringContainer,
            user_factory: TestUserFactory,
    ) -> None:
        # Create mock
        mock_service = MagicMock(spec= < Domain > Service)
        mock_service.get_by_id.side_effect = < Domain > NotFoundError("Mocked error")

        # Override BEFORE creating test client
        container.register( < Domain > Service, instance = mock_service)

        # Now create client
        user = user_factory()
        test_client_factory = TestClientFactory(container=container)
        with test_client_factory(auth_for_user=user) as test_client:
            response = test_client.get("/v1/<domain>s/1")

        assert response.status_code == HTTPStatus.NOT_FOUND
        mock_service.get_by_id.assert_called_once()
```

## Celery Task Test Pattern

```python
# tests/integration/tasks/test_<task>.py
import pytest

from delivery.tasks.tasks.<task> import <Task>Result
from tests.integration.factories import (
    TestCeleryWorkerFactory,
    TestTasksRegistryFactory,
)


class Test<Task>Task:
    @pytest.mark.django_db(transaction=True)
    def test_task_success(
        self,
        celery_worker_factory: TestCeleryWorkerFactory,
        tasks_registry_factory: TestTasksRegistryFactory,
    ) -> None:
        registry = tasks_registry_factory()

        with celery_worker_factory():
            result = registry.<task_name>.delay().get(timeout=5)

        assert result == <Task>Result(...)

    @pytest.mark.django_db(transaction=True)
    def test_task_with_arguments(
        self,
        celery_worker_factory: TestCeleryWorkerFactory,
        tasks_registry_factory: TestTasksRegistryFactory,
    ) -> None:
        registry = tasks_registry_factory()

        with celery_worker_factory():
            result = registry.<task_name>.delay(
                arg1="value1",
                arg2="value2",
            ).get(timeout=5)

        assert result["status"] == "success"
```

## Test Markers Reference

| Marker | When to Use |
|--------|-------------|
| `@pytest.mark.django_db` | Any test accessing the database |
| `@pytest.mark.django_db(transaction=True)` | Integration tests (required for proper isolation) |
| `@pytest.mark.slow` | Tests that take >1 second |

## Running Tests

```bash
# All tests
make test

# Specific file
pytest tests/integration/http/<domain>/test_<domain>.py -v

# Specific class
pytest tests/integration/http/<domain>/test_<domain>.py::TestCreate<Model> -v

# With coverage
pytest --cov=src --cov-report=html

# Skip slow tests
pytest -m "not slow"
```
