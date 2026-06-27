# Step 1: Model & Service Layer

Create the Todo domain model and service layer.

## What You'll Build

- A Django model for todo items
- A service class encapsulating database operations
- Domain exceptions for error handling

## Files to Create/Modify

| Action | File Path |
|--------|-----------|
| Create | `src/modern_python_template/core/todo/__init__.py` |
| Create | `src/modern_python_template/core/todo/apps.py` |
| Create | `src/modern_python_template/core/todo/models.py` |
| Create | `src/modern_python_template/core/todo/exceptions.py` |
| Create | `src/modern_python_template/core/todo/services.py` |
| Modify | `src/modern_python_template/infrastructure/django/settings.py` |

## Concept Reference

> **See also:** [Service Layer concept](../concepts/service-layer.md) for the theory behind this pattern.

## Step 1: Create the Todo App Directory

Create the directory structure for the todo domain:

```bash
mkdir -p src/modern_python_template/core/todo
touch src/modern_python_template/core/todo/__init__.py
```

Create `src/modern_python_template/core/todo/apps.py`:

```python
from django.apps import AppConfig


class TodoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modern_python_template.core.todo"
    label = "todo"
```

## Step 2: Define the Todo Model

Create the Django model in `src/modern_python_template/core/todo/models.py`:

```python
# src/modern_python_template/core/todo/models.py
from django.db import models

from modern_python_template.core.user.models import User


class Todo(models.Model):
    """A todo item belonging to a user."""

    title = models.CharField(verbose_name="title", max_length=200)
    description = models.TextField(verbose_name="description", blank=True, default="")
    completed = models.BooleanField(verbose_name="completed", default=False)
    created_at = models.DateTimeField(verbose_name="created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="updated at", auto_now=True)

    # Foreign key to User - each todo belongs to one user
    user: models.ForeignKey[User, User] = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name="todos",
        verbose_name="user",
    )

    class Meta:
        verbose_name = "todo"
        verbose_name_plural = "todos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "completed"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return self.title
```

Key points:

- `user` foreign key establishes ownership
- `related_name="todos"` allows `user.todos.all()`
- Explicit `verbose_name` values keep admin/forms human-readable
- The `models.ForeignKey[User, User]` annotation keeps model relationships typed
- Indexes improve query performance
- `ordering` sets default sort order

## Step 3: Register the App

Add the todo app to Django's installed apps. Edit `src/modern_python_template/infrastructure/django/settings.py`:

```python
# src/modern_python_template/infrastructure/django/settings.py
# Find the DjangoSettings class and add TodoConfig to installed_apps

class DjangoSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DJANGO_")

    installed_apps: tuple[str, ...] = (
        # Django apps
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        # Core apps
        "modern_python_template.core.user.apps.UserConfig",
        "modern_python_template.core.todo.apps.TodoConfig",  # Add this line
    )
```

## Step 4: Create and Apply Migrations

Generate the migration:

```bash
make makemigrations
```

You should see output like:

```
Migrations for 'todo':
  src/modern_python_template/core/todo/migrations/0001_initial.py
    - Create model Todo
```

Apply the migration:

```bash
make migrate
```

## Step 5: Create Domain Exceptions

Domain exceptions communicate specific errors. Create `src/modern_python_template/core/todo/exceptions.py`:

```python
# src/modern_python_template/core/todo/exceptions.py
from modern_python_template.core.exceptions import ApplicationError


class TodoNotFoundError(ApplicationError):
    """Raised when a todo item cannot be found."""


class TodoAccessDeniedError(ApplicationError):
    """Raised when a user tries to access another user's todo."""
```

## Step 6: Create the Todo Service

Create `src/modern_python_template/core/todo/services.py`:

```python
# src/modern_python_template/core/todo/services.py
from dataclasses import dataclass

from asgiref.sync import sync_to_async
from diwire import Injected

from modern_python_template.core.todo.exceptions import TodoAccessDeniedError, TodoNotFoundError
from modern_python_template.foundation.services import BaseService
from modern_python_template.foundation.transactions import TransactionFactory
from modern_python_template.core.todo.models import Todo
from modern_python_template.core.user.models import User


@dataclass(kw_only=True)
class TodoService(BaseService):
    """Service for todo item operations.

    Encapsulates all database operations for Todo model.
    Controllers should use this service instead of accessing Todo directly.
    """

    _transaction_factory: Injected[TransactionFactory]

    async def get_todo_by_id(self, *, todo_id: int, user: User) -> Todo:
        """Get a todo by ID, ensuring it belongs to the user.

        Args:
            todo_id: The todo's primary key.
            user: The requesting user.

        Returns:
            The Todo instance.

        Raises:
            TodoNotFoundError: If the todo doesn't exist.
            TodoAccessDeniedError: If the todo belongs to another user.
        """
        return await sync_to_async(
            self._get_todo_by_id,
            thread_sensitive=True,
        )(todo_id=todo_id, user=user)

    def _get_todo_by_id(self, *, todo_id: int, user: User) -> Todo:
        try:
            todo = Todo.objects.get(id=todo_id)
        except Todo.DoesNotExist as e:
            raise TodoNotFoundError(f"Todo {todo_id} not found") from e

        if todo.user_id != user.id:
            raise TodoAccessDeniedError("Cannot access another user's todo")

        return todo

    async def list_todos_for_user(
        self,
        *,
        user: User,
        completed: bool | None = None,
    ) -> list[Todo]:
        """List all todos for a user.

        Args:
            user: The user whose todos to list.
            completed: Optional filter for completion status.

        Returns:
            List of Todo instances.
        """
        return await sync_to_async(
            self._list_todos_for_user,
            thread_sensitive=True,
        )(user=user, completed=completed)

    def _list_todos_for_user(
        self,
        *,
        user: User,
        completed: bool | None = None,
    ) -> list[Todo]:
        queryset = Todo.objects.filter(user=user)

        if completed is not None:
            queryset = queryset.filter(completed=completed)

        return list(queryset)

    async def create_todo(
        self,
        *,
        user: User,
        title: str,
        description: str = "",
    ) -> Todo:
        """Create a new todo for a user.

        Args:
            user: The owner of the todo.
            title: The todo title.
            description: Optional description.

        Returns:
            The created Todo instance.
        """
        return await sync_to_async(
            self._create_todo_transactionally,
            thread_sensitive=True,
        )(user=user, title=title, description=description)

    def _create_todo_transactionally(
        self,
        *,
        user: User,
        title: str,
        description: str = "",
    ) -> Todo:
        with self._transaction_factory(span_name="create todo"):
            return Todo.objects.create(
                user=user,
                title=title,
                description=description,
            )

    async def update_todo(
        self,
        *,
        todo_id: int,
        user: User,
        title: str | None = None,
        description: str | None = None,
        completed: bool | None = None,
    ) -> Todo:
        """Update a todo item.

        Args:
            todo_id: The todo's primary key.
            user: The requesting user.
            title: New title (optional).
            description: New description (optional).
            completed: New completion status (optional).

        Returns:
            The updated Todo instance.

        Raises:
            TodoNotFoundError: If the todo doesn't exist.
            TodoAccessDeniedError: If the todo belongs to another user.
        """
        return await sync_to_async(
            self._update_todo_transactionally,
            thread_sensitive=True,
        )(
            todo_id=todo_id,
            user=user,
            title=title,
            description=description,
            completed=completed,
        )

    def _update_todo_transactionally(
        self,
        *,
        todo_id: int,
        user: User,
        title: str | None = None,
        description: str | None = None,
        completed: bool | None = None,
    ) -> Todo:
        with self._transaction_factory(span_name="update todo"):
            todo = self._get_todo_by_id(todo_id=todo_id, user=user)

            if title is not None:
                todo.title = title
            if description is not None:
                todo.description = description
            if completed is not None:
                todo.completed = completed

            todo.save()
            return todo

    async def delete_todo(self, *, todo_id: int, user: User) -> None:
        """Delete a todo item.

        Args:
            todo_id: The todo's primary key.
            user: The requesting user.

        Raises:
            TodoNotFoundError: If the todo doesn't exist.
            TodoAccessDeniedError: If the todo belongs to another user.
        """
        await sync_to_async(
            self._delete_todo_transactionally,
            thread_sensitive=True,
        )(todo_id=todo_id, user=user)

    def _delete_todo_transactionally(self, *, todo_id: int, user: User) -> None:
        with self._transaction_factory(span_name="delete todo"):
            todo = self._get_todo_by_id(todo_id=todo_id, user=user)
            todo.delete()

    async def mark_completed(self, *, todo_id: int, user: User) -> Todo:
        """Mark a todo as completed.

        Args:
            todo_id: The todo's primary key.
            user: The requesting user.

        Returns:
            The updated Todo instance.
        """
        return await self.update_todo(todo_id=todo_id, user=user, completed=True)

    async def mark_incomplete(self, *, todo_id: int, user: User) -> Todo:
        """Mark a todo as incomplete.

        Args:
            todo_id: The todo's primary key.
            user: The requesting user.

        Returns:
            The updated Todo instance.
        """
        return await self.update_todo(todo_id=todo_id, user=user, completed=False)

    async def delete_completed_todos(self, *, user: User) -> int:
        """Delete all completed todos for a user.

        Args:
            user: The user whose completed todos to delete.

        Returns:
            Number of todos deleted.
        """
        return await sync_to_async(
            self._delete_completed_todos_transactionally,
            thread_sensitive=True,
        )(user=user)

    def _delete_completed_todos_transactionally(self, *, user: User) -> int:
        with self._transaction_factory(span_name="delete completed todos"):
            deleted_count, _ = Todo.objects.filter(
                user=user,
                completed=True,
            ).delete()
            return deleted_count
```

## Understanding the Service Pattern

### Why Use Services?

1. **Testability**: Test business logic without HTTP concerns
2. **Reusability**: Same service for HTTP, Celery, CLI
3. **Encapsulation**: Database operations are hidden from controllers
4. **Transaction Management**: `TransactionFactory` keeps transaction behavior injectable

### Key Patterns in This Service

**Domain Exceptions**: `TodoNotFoundError` and `TodoAccessDeniedError` communicate specific errors that controllers can map to HTTP responses.

**Ownership Checks**: `get_todo_by_id` verifies the user owns the todo before returning it.

**Type Hints**: All methods have complete type annotations for `mypy --strict`.

**Docstrings**: Google-style docstrings document args, returns, and raises.

## Verification

Test the service in a Django shell:

```bash
uv run python management/manage.py shell
```

```python
import asyncio

from asgiref.sync import sync_to_async

from modern_python_template.core.user.models import User
from modern_python_template.core.todo.services import TodoService
from modern_python_template.infrastructure.django.transactions import DjangoTransactionFactory


async def main() -> None:
    # Get or create a test user
    user = await User.objects.afirst()
    if not user:
        user = await sync_to_async(User.objects.create_user, thread_sensitive=True)(
            username="testuser",
            email="test@example.com",
            password="password",
        )

    # Create a service instance
    service = TodoService(_transaction_factory=DjangoTransactionFactory())

    # Create a todo
    todo = await service.create_todo(
        user=user,
        title="Learn modern-python-template",
        description="Complete the tutorial",
    )
    print(f"Created: {todo.title}")

    # List todos
    todos = await service.list_todos_for_user(user=user)
    print(f"User has {len(todos)} todos")

    # Mark complete
    todo = await service.mark_completed(todo_id=todo.id, user=user)
    print(f"Completed: {todo.completed}")


asyncio.run(main())
```

## Summary

You've created:

- A `Todo` Django model with user ownership
- A `TodoService` with CRUD operations
- Domain exceptions in `exceptions.py` for error handling
- Database indexes for performance

## Next Step

In [Step 2: IoC Registration](02-ioc-registration.md), you'll learn how the IoC container automatically wires dependencies.
