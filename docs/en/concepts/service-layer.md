# Service Layer

The service layer is the core architectural pattern that separates business logic from HTTP/Celery concerns.

## The Problem

Without a service layer, controllers directly access the database:

```python
# ❌ Wrong - Controller accesses model directly
from core.user.models import User

class UserController:
    def get_user(self, user_id: int) -> UserSchema:
        user = User.objects.get(id=user_id)  # Direct ORM access
        return UserSchema.model_validate(user, from_attributes=True)
```

This causes problems:

1. **Testing is hard**: You must test HTTP to test business logic
2. **Code duplication**: Same logic needed in Celery tasks, CLI, etc.
3. **Tight coupling**: Changes to models affect all controllers
4. **Security risks**: Authorization logic scattered across controllers

## The Solution

The service layer acts as an intermediary:

```python
# ✅ Correct - Controller uses service
from core.user.services import UserService

class UserController:
    def __init__(self, user_service: UserService) -> None:
        self._user_service = user_service

    def get_user(self, user_id: int) -> UserSchema:
        user = self._user_service.get_user_by_id(user_id)
        return UserSchema.model_validate(user, from_attributes=True)
```

## The Golden Rule

```
Controller → Service → Model

✅ Controller imports Service
✅ Service imports Model
❌ Controller imports Model (NEVER)
```

This boundary is absolute. Controllers never import models.

## Service Structure

Services are dataclasses with injected dependencies:

```python
# src/core/todo/services.py
from dataclasses import dataclass

from django.db import transaction

from core.todo.models import Todo
from core.user.models import User


class TodoNotFoundError(Exception):
    """Domain exception for missing todos."""


@dataclass(kw_only=True)
class TodoService:
    """Service for todo operations."""

    def get_todo_by_id(self, todo_id: int) -> Todo:
        try:
            return Todo.objects.get(id=todo_id)
        except Todo.DoesNotExist as e:
            raise TodoNotFoundError(f"Todo {todo_id} not found") from e

    def list_todos(self) -> list[Todo]:
        return list(Todo.objects.all())

    @transaction.atomic
    def create_todo(self, user: User, title: str) -> Todo:
        return Todo.objects.create(user=user, title=title)
```

### Return Value Patterns

Services can use two patterns for "not found" scenarios:

=== "Exception pattern"
    ```python
    def get_todo_by_id(self, todo_id: int) -> Todo:
        try:
            return Todo.objects.get(id=todo_id)
        except Todo.DoesNotExist as e:
            raise TodoNotFoundError(f"Todo {todo_id} not found") from e
    ```
    - Use when the item should exist (e.g., accessing a known resource)
    - Controller's `handle_exception()` maps to HTTP 404

=== "None pattern"
    ```python
    def get_user_by_id(self, user_id: int) -> User | None:
        return User.objects.filter(id=user_id).first()
    ```
    - Use when absence is a normal case (e.g., lookup by credentials)
    - Controller explicitly checks for `None` and responds accordingly

!!! tip "Choosing a pattern"
    The existing `UserService` uses the **None pattern** because user lookups often occur during authentication where "not found" is expected. Choose the pattern that fits your domain semantics.

## Benefits

### 1. Testability

Test business logic without HTTP:

```python
def test_create_todo():
    service = TodoService()
    todo = service.create_todo(user, "Test")
    assert todo.title == "Test"
```

### 2. Reusability

Same service works everywhere:

```python
# HTTP Controller
class TodoController:
    def create(self, body: CreateTodoSchema) -> TodoSchema:
        todo = self._service.create_todo(user, body.title)
        return TodoSchema.model_validate(todo, from_attributes=True)

# Celery Task
class ImportTaskController:
    def import_todos(self, titles: list[str]) -> None:
        for title in titles:
            self._service.create_todo(user, title)
```

### 3. Clear Boundaries

Each layer has a single responsibility:

| Layer | Responsibility |
|-------|----------------|
| Controller | HTTP/Celery concerns, serialization |
| Service | Business logic, database operations |
| Model | Data structure, database schema |

### 4. Domain Exceptions

Services raise meaningful exceptions:

```python
class TodoNotFoundError(ApplicationError):
    """Raised when a todo cannot be found."""

class TodoAccessDeniedError(ApplicationError):
    """Raised when a user cannot access a todo."""
```

Controllers map these to HTTP responses:

```python
def handle_exception(self, exception: Exception) -> Any:
    if isinstance(exception, TodoNotFoundError):
        raise HTTPException(status_code=404, detail=str(exception))
    if isinstance(exception, TodoAccessDeniedError):
        raise HTTPException(status_code=403, detail=str(exception))
    return super().handle_exception(exception)
```

## Transaction Management

Use `@transaction.atomic` for database writes:

```python
from django.db import transaction

@dataclass(kw_only=True)
class TodoService:
    @transaction.atomic
    def create_todo(self, user: User, title: str) -> Todo:
        todo = Todo.objects.create(user=user, title=title)
        # If anything fails here, the transaction rolls back
        self._audit_service.log_creation(todo)
        return todo
```

The `TransactionController` also wraps methods in transactions automatically.

## Acceptable Exceptions

Model imports are acceptable in:

### Django Admin

```python
# src/core/todo/admin.py
from django.contrib import admin
from core.todo.models import Todo  # ✅ OK in admin

@admin.register(Todo)
class TodoAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "completed"]
```

### Migrations

```python
# Auto-generated by Django
from django.db import migrations, models
```

### Tests (for data creation)

```python
# tests/integration/conftest.py
from core.todo.models import Todo  # ✅ OK in tests

@pytest.fixture
def todo(user: User) -> Todo:
    return Todo.objects.create(user=user, title="Test")
```

## Type Hints with Models

Controllers can reference models in type hints for validation, but must use services for operations:

```python
from core.user.models import User  # For type hint only

def get_user(self, request: AuthenticatedRequest) -> UserSchema:
    user: User = request.state.user  # Type hint is fine
    # But operations go through service
    return self._user_service.get_user_details(user.id)
```

## Service Dependencies

Services can depend on other services:

```python
@dataclass(kw_only=True)
class OrderService:
    _user_service: UserService
    _payment_service: PaymentService
    _notification_service: NotificationService

    @transaction.atomic
    def create_order(self, user_id: int, items: list[Item]) -> Order:
        user = self._user_service.get_user_by_id(user_id)
        order = Order.objects.create(user=user)
        self._payment_service.charge(user, order.total)
        self._notification_service.send_confirmation(user, order)
        return order
```

The IoC container resolves the entire dependency graph automatically.

## Summary

The service layer:

- **Encapsulates** all database operations
- **Provides** reusable business logic
- **Enables** easy testing
- **Defines** domain exceptions
- **Manages** transactions

Controllers use services; they never access models directly.
