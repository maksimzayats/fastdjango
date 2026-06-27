# Service Layer

The service layer is the core architectural pattern that separates business logic from HTTP/Celery concerns.

## The Problem

Without a service layer, controllers directly access the database:

```python
# ❌ Wrong - Controller accesses model directly
from modern_python_template.core.user.models import User

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

The service layer acts as an intermediary. FastAPI-facing workflows are async:

```python
# ✅ Correct - Controller uses a use case or service
from modern_python_template.core.user.use_cases import UserUseCase

class UserController:
    def __init__(self, user_use_case: UserUseCase) -> None:
        self._user_use_case = user_use_case

    async def get_user(self, user_id: int) -> UserSchema:
        user = await self._user_use_case.get_user_by_id(user_id=user_id)
        return UserSchema.model_validate(user, from_attributes=True)
```

## The Golden Rule

```
Controller → Use Case / Service → Model

✅ Controller calls a use case or service
✅ Use cases and services own ORM access
❌ Controller queries models directly
```

This boundary is absolute: controllers handle delivery concerns, not ORM queries.

## Service Structure

Services are dataclasses with injected dependencies:

```python
# src/modern_python_template/core/todo/services.py
from dataclasses import dataclass

from diwire import Injected

from modern_python_template.core.todo.exceptions import TodoNotFoundError
from modern_python_template.foundation.services import BaseService
from modern_python_template.foundation.transactions import TransactionFactory
from modern_python_template.core.todo.models import Todo
from modern_python_template.core.user.models import User


@dataclass(kw_only=True)
class TodoService(BaseService):
    """Service for todo operations."""

    _transaction_factory: Injected[TransactionFactory]

    async def get_todo_by_id(self, *, todo_id: int) -> Todo:
        try:
            return await Todo.objects.aget(id=todo_id)
        except Todo.DoesNotExist as e:
            raise TodoNotFoundError(f"Todo {todo_id} not found") from e

    async def list_todos(self) -> list[Todo]:
        return [todo async for todo in Todo.objects.all()]

    async def create_todo(self, *, user: User, title: str) -> Todo:
        return await sync_to_async(
            self._create_todo_transactionally,
            thread_sensitive=True,
        )(user=user, title=title)

    def _create_todo_transactionally(self, *, user: User, title: str) -> Todo:
        with self._transaction_factory(span_name="create todo"):
            return Todo.objects.create(user=user, title=title)
```

Django transactions are sync-only. Keep them in short methods named
`*_transactionally` and call them from async orchestration with
`sync_to_async(..., thread_sensitive=True)`.

### Return Value Patterns

Services can use two patterns for "not found" scenarios:

=== "Exception pattern"
    ```python
    def get_todo_by_id(self, *, todo_id: int) -> Todo:
        try:
            return Todo.objects.get(id=todo_id)
        except Todo.DoesNotExist as e:
            raise TodoNotFoundError(f"Todo {todo_id} not found") from e
    ```
    - Use when the item should exist (e.g., accessing a known resource)
    - Controller's `handle_exception()` maps to HTTP 404

=== "None pattern"
    ```python
    def get_user_by_id(self, *, user_id: int) -> User | None:
        return User.objects.filter(id=user_id).first()
    ```
    - Use when absence is a normal case (e.g., lookup by credentials)
    - Controller explicitly checks for `None` and responds accordingly

!!! tip "Choosing a pattern"
    The existing `UserUseCase` uses the **None pattern** because user lookups often occur during authentication where "not found" is expected. Choose the pattern that fits your domain semantics.

## Benefits

### 1. Testability

Test business logic without HTTP:

```python
@pytest.mark.anyio
async def test_create_todo() -> None:
    service = TodoService(_transaction_factory=DjangoTransactionFactory())
    todo = await service.create_todo(user=user, title="Test")
    assert todo.title == "Test"
```

### 2. Reusability

Same service works everywhere:

```python
# HTTP Controller
class TodoController(BaseAsyncController):
    async def create(self, body: CreateTodoSchema) -> TodoSchema:
        todo = await self._service.create_todo(user=user, title=body.title)
        return TodoSchema.model_validate(todo, from_attributes=True)

# Celery Task
class ImportTaskController(BaseCeleryTaskController):
    async def import_todos(self, *, titles: list[str]) -> None:
        for title in titles:
            await self._service.create_todo(user=user, title=title)
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
# src/modern_python_template/core/todo/exceptions.py
from modern_python_template.core.exceptions import ApplicationError


class TodoNotFoundError(ApplicationError):
    """Raised when a todo cannot be found."""

class TodoAccessDeniedError(ApplicationError):
    """Raised when a user cannot access a todo."""
```

Controllers map these to HTTP responses:

```python
async def handle_exception(self, exception: Exception) -> Any:
    if isinstance(exception, TodoNotFoundError):
        raise HTTPException(status_code=404, detail=str(exception))
    if isinstance(exception, TodoAccessDeniedError):
        raise HTTPException(status_code=403, detail=str(exception))
    return await super().handle_exception(exception)
```

## Transaction Management

Use a short sync transaction island for database writes:

```python
from diwire import Injected

from modern_python_template.foundation.services import BaseService
from modern_python_template.foundation.transactions import TransactionFactory

@dataclass(kw_only=True)
class TodoService(BaseService):
    _transaction_factory: Injected[TransactionFactory]

    async def create_todo(self, *, user: User, title: str) -> Todo:
        return await sync_to_async(
            self._create_todo_transactionally,
            thread_sensitive=True,
        )(user=user, title=title)

    def _create_todo_transactionally(self, *, user: User, title: str) -> Todo:
        with self._transaction_factory(span_name="create todo"):
            todo = Todo.objects.create(user=user, title=title)
            # If anything fails here, the transaction rolls back
            self._audit_service.log_creation(todo)
            return todo
```

FastAPI controllers stay async and do not wrap whole request handlers in
transactions.

## Acceptable Exceptions

Model imports are acceptable in:

### Django Admin

```python
# src/modern_python_template/core/todo/delivery/django/admin.py
from django.contrib import admin
from modern_python_template.core.todo.models import Todo  # ✅ OK in admin

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
from modern_python_template.core.todo.models import Todo  # ✅ OK in tests

@pytest.fixture
def todo(user: User) -> Todo:
    return Todo.objects.create(user=user, title="Test")
```

## Type Hints with Models

Controllers can reference models in type hints for validation, but must use services for operations:

```python
from modern_python_template.core.user.models import User  # For type hint only

async def get_user(self, request: AuthenticatedRequest) -> UserSchema:
    user: User = request.state.user  # Type hint is fine
    # But operations go through service
    return await self._user_use_case.get_user_details(user_id=user.id)
```

## Service Dependencies

Services can depend on other services:

```python
from modern_python_template.foundation.services import BaseService

@dataclass(kw_only=True)
class OrderService(BaseService):
    _user_use_case: Injected[UserUseCase]
    _payment_service: Injected[PaymentService]
    _notification_service: Injected[NotificationService]
    _transaction_factory: Injected[TransactionFactory]

    async def create_order(self, *, user_id: int, items: list[Item]) -> Order:
        user = await self._user_use_case.get_user_by_id(user_id=user_id)
        payment = await self._payment_service.authorize(user=user, items=items)
        order = await sync_to_async(
            self._create_order_transactionally,
            thread_sensitive=True,
        )(user=user, items=items, payment=payment)
        await self._notification_service.send_confirmation(user=user, order=order)
        return order

    def _create_order_transactionally(
        self,
        *,
        user: User,
        items: list[Item],
        payment: PaymentAuthorization,
    ) -> Order:
        with self._transaction_factory(span_name="create order"):
            order = Order.objects.create(user=user)
            Payment.objects.create(order=order, authorization_id=payment.id)
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
