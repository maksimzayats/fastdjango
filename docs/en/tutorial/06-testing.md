# Step 6: Testing

Write comprehensive tests for the Todo feature.

## What You'll Build

- Integration tests for HTTP endpoints
- Service unit tests
- Celery task tests
- IoC override patterns for mocking

## Files to Create

| Action | File Path |
|--------|-----------|
| Create | `tests/integration/http/v1/test_v1_todos.py` |
| Create | `tests/unit/services/test_todo_service.py` |

## Concept Reference

> **See also:** [Override IoC in Tests guide](../how-to/override-ioc-in-tests.md) for mocking techniques.

## Understanding the Test Architecture

The project uses:

- **pytest** for test framework
- **pytest-django** for Django integration
- **Function-scoped containers** for test isolation
- **Test factories** for creating test data

## Step 1: Create HTTP Integration Tests

Create `tests/integration/http/v1/test_v1_todos.py`:

```python
# tests/integration/http/v1/test_v1_todos.py
from http import HTTPStatus

import pytest

from core.todo.models import Todo
from core.todo.services import TodoService
from core.user.models import User
from tests.integration.factories import TestClientFactory, TestUserFactory


@pytest.fixture(scope="function")
def user(user_factory: TestUserFactory) -> User:
    """Create a test user."""
    return user_factory(
        username="testuser",
        password="SecurePassword123!",
        email="test@example.com",
    )


@pytest.fixture(scope="function")
def other_user(user_factory: TestUserFactory) -> User:
    """Create another test user for access control tests."""
    return user_factory(
        username="otheruser",
        password="SecurePassword123!",
        email="other@example.com",
    )


@pytest.fixture(scope="function")
def todo(user: User) -> Todo:
    """Create a test todo."""
    return Todo.objects.create(
        user=user,
        title="Test Todo",
        description="Test description",
    )


@pytest.mark.django_db(transaction=True)
class TestTodoController:
    """Tests for todo HTTP endpoints."""

    def test_list_todos_empty(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        """Test listing todos when user has none."""
        with test_client_factory(auth_for_user=user) as client:
            response = client.get("/v1/todos")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["todos"] == []
        assert data["count"] == 0

    def test_list_todos_with_items(
        self,
        test_client_factory: TestClientFactory,
        user: User,
        todo: Todo,
    ) -> None:
        """Test listing todos returns user's items."""
        with test_client_factory(auth_for_user=user) as client:
            response = client.get("/v1/todos")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["count"] == 1
        assert data["todos"][0]["title"] == "Test Todo"

    def test_list_todos_filter_completed(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        """Test filtering todos by completion status."""
        # Create completed and incomplete todos
        Todo.objects.create(user=user, title="Completed", completed=True)
        Todo.objects.create(user=user, title="Incomplete", completed=False)

        with test_client_factory(auth_for_user=user) as client:
            response = client.get("/v1/todos?completed=true")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["count"] == 1
        assert data["todos"][0]["title"] == "Completed"

    def test_create_todo(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        """Test creating a new todo."""
        with test_client_factory(auth_for_user=user) as client:
            response = client.post(
                "/v1/todos",
                json={
                    "title": "New Todo",
                    "description": "New description",
                },
            )

        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert data["title"] == "New Todo"
        assert data["description"] == "New description"
        assert data["completed"] is False
        assert data["user_id"] == user.id

    def test_create_todo_minimal(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        """Test creating a todo with minimal fields."""
        with test_client_factory(auth_for_user=user) as client:
            response = client.post(
                "/v1/todos",
                json={"title": "Minimal Todo"},
            )

        assert response.status_code == HTTPStatus.CREATED
        data = response.json()
        assert data["title"] == "Minimal Todo"
        assert data["description"] == ""

    def test_create_todo_validation_error(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        """Test creating a todo with invalid data."""
        with test_client_factory(auth_for_user=user) as client:
            response = client.post(
                "/v1/todos",
                json={"title": ""},  # Empty title
            )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_get_todo(
        self,
        test_client_factory: TestClientFactory,
        user: User,
        todo: Todo,
    ) -> None:
        """Test getting a specific todo."""
        with test_client_factory(auth_for_user=user) as client:
            response = client.get(f"/v1/todos/{todo.id}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["id"] == todo.id
        assert data["title"] == "Test Todo"

    def test_get_todo_not_found(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        """Test getting a non-existent todo."""
        with test_client_factory(auth_for_user=user) as client:
            response = client.get("/v1/todos/99999")

        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_get_todo_access_denied(
        self,
        test_client_factory: TestClientFactory,
        other_user: User,
        todo: Todo,
    ) -> None:
        """Test accessing another user's todo."""
        with test_client_factory(auth_for_user=other_user) as client:
            response = client.get(f"/v1/todos/{todo.id}")

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_update_todo(
        self,
        test_client_factory: TestClientFactory,
        user: User,
        todo: Todo,
    ) -> None:
        """Test updating a todo."""
        with test_client_factory(auth_for_user=user) as client:
            response = client.patch(
                f"/v1/todos/{todo.id}",
                json={
                    "title": "Updated Title",
                    "completed": True,
                },
            )

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["completed"] is True

    def test_update_todo_partial(
        self,
        test_client_factory: TestClientFactory,
        user: User,
        todo: Todo,
    ) -> None:
        """Test partial update of a todo."""
        original_title = todo.title

        with test_client_factory(auth_for_user=user) as client:
            response = client.patch(
                f"/v1/todos/{todo.id}",
                json={"completed": True},
            )

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data["title"] == original_title  # Unchanged
        assert data["completed"] is True

    def test_delete_todo(
        self,
        test_client_factory: TestClientFactory,
        user: User,
        todo: Todo,
    ) -> None:
        """Test deleting a todo."""
        todo_id = todo.id

        with test_client_factory(auth_for_user=user) as client:
            response = client.delete(f"/v1/todos/{todo_id}")

        assert response.status_code == HTTPStatus.NO_CONTENT
        assert not Todo.objects.filter(id=todo_id).exists()

    def test_unauthenticated_access(
        self,
        test_client_factory: TestClientFactory,
    ) -> None:
        """Test that unauthenticated requests are rejected."""
        with test_client_factory() as client:  # No auth
            response = client.get("/v1/todos")

        assert response.status_code == HTTPStatus.FORBIDDEN
```

## Step 2: Create Service Unit Tests

Create `tests/unit/services/test_todo_service.py`:

```python
# tests/unit/services/test_todo_service.py
import pytest

from core.todo.models import Todo
from core.todo.services import (
    TodoAccessDeniedError,
    TodoNotFoundError,
    TodoService,
)
from core.user.models import User


@pytest.fixture(scope="function")
def service() -> TodoService:
    """Create a TodoService instance."""
    return TodoService()


@pytest.fixture(scope="function")
def user(transactional_db: None) -> User:
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="password",
    )


@pytest.fixture(scope="function")
def other_user(transactional_db: None) -> User:
    """Create another test user."""
    return User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="password",
    )


@pytest.mark.django_db(transaction=True)
class TestTodoService:
    """Unit tests for TodoService."""

    def test_create_todo(self, service: TodoService, user: User) -> None:
        """Test creating a todo."""
        todo = service.create_todo(
            user,
            title="Test Todo",
            description="Test description",
        )

        assert todo.id is not None
        assert todo.title == "Test Todo"
        assert todo.description == "Test description"
        assert todo.completed is False
        assert todo.user_id == user.id

    def test_get_todo_by_id(self, service: TodoService, user: User) -> None:
        """Test getting a todo by ID."""
        created = service.create_todo(user, title="Test")
        retrieved = service.get_todo_by_id(created.id, user)

        assert retrieved.id == created.id

    def test_get_todo_by_id_not_found(
        self,
        service: TodoService,
        user: User,
    ) -> None:
        """Test getting a non-existent todo."""
        with pytest.raises(TodoNotFoundError):
            service.get_todo_by_id(99999, user)

    def test_get_todo_by_id_access_denied(
        self,
        service: TodoService,
        user: User,
        other_user: User,
    ) -> None:
        """Test accessing another user's todo."""
        todo = service.create_todo(user, title="Private Todo")

        with pytest.raises(TodoAccessDeniedError):
            service.get_todo_by_id(todo.id, other_user)

    def test_list_todos_for_user(
        self,
        service: TodoService,
        user: User,
    ) -> None:
        """Test listing todos for a user."""
        service.create_todo(user, title="Todo 1")
        service.create_todo(user, title="Todo 2")

        todos = service.list_todos_for_user(user)

        assert len(todos) == 2

    def test_list_todos_filter_completed(
        self,
        service: TodoService,
        user: User,
    ) -> None:
        """Test filtering todos by completion status."""
        service.create_todo(user, title="Incomplete")
        completed = service.create_todo(user, title="Completed")
        service.mark_completed(completed.id, user)

        incomplete_todos = service.list_todos_for_user(user, completed=False)
        completed_todos = service.list_todos_for_user(user, completed=True)

        assert len(incomplete_todos) == 1
        assert len(completed_todos) == 1

    def test_update_todo(self, service: TodoService, user: User) -> None:
        """Test updating a todo."""
        todo = service.create_todo(user, title="Original")

        updated = service.update_todo(
            todo.id,
            user,
            title="Updated",
            completed=True,
        )

        assert updated.title == "Updated"
        assert updated.completed is True

    def test_delete_todo(self, service: TodoService, user: User) -> None:
        """Test deleting a todo."""
        todo = service.create_todo(user, title="To Delete")

        service.delete_todo(todo.id, user)

        assert not Todo.objects.filter(id=todo.id).exists()

    def test_mark_completed(self, service: TodoService, user: User) -> None:
        """Test marking a todo as completed."""
        todo = service.create_todo(user, title="Test")

        result = service.mark_completed(todo.id, user)

        assert result.completed is True

    def test_mark_incomplete(self, service: TodoService, user: User) -> None:
        """Test marking a todo as incomplete."""
        todo = service.create_todo(user, title="Test")
        service.mark_completed(todo.id, user)

        result = service.mark_incomplete(todo.id, user)

        assert result.completed is False

    def test_delete_completed_todos(
        self,
        service: TodoService,
        user: User,
    ) -> None:
        """Test deleting all completed todos."""
        service.create_todo(user, title="Keep")
        completed1 = service.create_todo(user, title="Delete 1")
        completed2 = service.create_todo(user, title="Delete 2")
        service.mark_completed(completed1.id, user)
        service.mark_completed(completed2.id, user)

        deleted_count = service.delete_completed_todos(user)

        assert deleted_count == 2
        assert Todo.objects.filter(user=user).count() == 1
```

## Step 3: Create Celery Task Tests

Add task tests to `tests/integration/tasks/test_todo_cleanup.py`:

```python
# tests/integration/tasks/test_todo_cleanup.py
import pytest

from core.todo.models import Todo
from core.user.models import User
from tests.integration.factories import (
    TestCeleryWorkerFactory,
    TestTasksRegistryFactory,
    TestUserFactory,
)


@pytest.fixture(scope="function")
def user(user_factory: TestUserFactory) -> User:
    """Create a test user."""
    return user_factory(username="testuser", password="password")


@pytest.mark.django_db(transaction=True)
class TestTodoCleanupTask:
    """Tests for todo cleanup Celery task."""

    def test_cleanup_completed_todos(
        self,
        celery_worker_factory: TestCeleryWorkerFactory,
        tasks_registry_factory: TestTasksRegistryFactory,
        user: User,
    ) -> None:
        """Test that cleanup task deletes completed todos."""
        # Create test data
        Todo.objects.create(user=user, title="Keep", completed=False)
        Todo.objects.create(user=user, title="Delete", completed=True)

        registry = tasks_registry_factory()

        with celery_worker_factory():
            result = registry.todo_cleanup.delay().get(timeout=10)

        assert result["todos_deleted"] == 1
        assert Todo.objects.filter(user=user).count() == 1
```

## Running Tests

```bash
# Run all tests
make test

# Run with coverage report
pytest --cov=src --cov-report=html tests/

# Run specific test file
pytest tests/integration/http/v1/test_v1_todos.py

# Run with verbose output
pytest -v tests/

# Run specific test class
pytest tests/integration/http/v1/test_v1_todos.py::TestTodoController

# Run specific test method
pytest tests/integration/http/v1/test_v1_todos.py::TestTodoController::test_create_todo
```

## Test Patterns

### Using Test Factories

```python
# TestClientFactory - HTTP testing with optional auth
with test_client_factory(auth_for_user=user) as client:
    response = client.get("/v1/todos")

# TestUserFactory - Create test users
user = user_factory(username="test", password="pass")

# TestCeleryWorkerFactory - Run Celery workers
with celery_worker_factory():
    result = registry.my_task.delay().get(timeout=10)
```

### Per-Test Isolation

Each test gets a fresh container. Fixtures are function-scoped by default:

```python
@pytest.fixture(scope="function")
def container() -> Container:
    return ContainerFactory()()
```

### Transaction Rollback

Use `@pytest.mark.django_db(transaction=True)` for database tests:

```python
@pytest.mark.django_db(transaction=True)
class TestMyFeature:
    def test_something(self) -> None:
        # Database changes are rolled back after test
        ...
```

## Summary

You've learned:

- Integration testing HTTP endpoints with `TestClientFactory`
- Unit testing services directly
- Testing Celery tasks with `TestCeleryWorkerFactory`
- Test isolation patterns and fixtures

## Congratulations!

You've completed the tutorial! You now know how to:

1. Create Django models with proper relationships
2. Build services that encapsulate business logic
3. Wire dependencies with the IoC container
4. Create HTTP endpoints with authentication
5. Add background task processing
6. Configure observability
7. Write comprehensive tests

## Next Steps

- [Concepts](../concepts/index.md) - Deeper understanding of the architecture
- [How-To Guides](../how-to/index.md) - Solve specific problems
- [Reference](../reference/index.md) - Complete configuration details
