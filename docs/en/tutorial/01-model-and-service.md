# Step 1: Model & Service Layer

Create the Todo domain model and service layer.

## What You'll Build

- A Django model for todo items
- A service class encapsulating database operations
- Domain exceptions for error handling

## Files to Create/Modify

| Action | File Path |
|--------|-----------|
| Create | `src/core/todo/__init__.py` |
| Create | `src/core/todo/models.py` |
| Create | `src/core/todo/services.py` |
| Modify | `src/configs/django.py` |

## Concept Reference

> **See also:** [Service Layer concept](../concepts/service-layer.md) for the theory behind this pattern.

## Step 1: Create the Todo App Directory

Create the directory structure for the todo domain:

```bash
mkdir -p src/core/todo
touch src/core/todo/__init__.py
```

## Step 2: Define the Todo Model

Create the Django model in `src/core/todo/models.py`:

```python
# src/core/todo/models.py
from django.db import models

from core.user.models import User


class Todo(models.Model):
    """A todo item belonging to a user."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Foreign key to User - each todo belongs to one user
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="todos",
    )

    class Meta:
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
- Indexes improve query performance
- `ordering` sets default sort order

## Step 3: Register the App

Add the todo app to Django's installed apps. Edit `src/configs/django.py`:

```python
# src/configs/django.py
# Find the DjangoSettings class and add 'core.todo' to installed_apps

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
        "core.user",
        "core.todo",  # Add this line
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
  src/core/todo/migrations/0001_initial.py
    - Create model Todo
```

Apply the migration:

```bash
make migrate
```

## Step 5: Create Domain Exceptions

Domain exceptions communicate specific errors. Add them to the service file.

## Step 6: Create the Todo Service

Create `src/core/todo/services.py`:

```python
# src/core/todo/services.py
from dataclasses import dataclass

from django.db import transaction

from core.exceptions import ApplicationError
from core.todo.models import Todo
from core.user.models import User


class TodoNotFoundError(ApplicationError):
    """Raised when a todo item cannot be found."""


class TodoAccessDeniedError(ApplicationError):
    """Raised when a user tries to access another user's todo."""


@dataclass(kw_only=True)
class TodoService:
    """Service for todo item operations.

    Encapsulates all database operations for Todo model.
    Controllers should use this service instead of accessing Todo directly.
    """

    def get_todo_by_id(self, todo_id: int, user: User) -> Todo:
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
        try:
            todo = Todo.objects.get(id=todo_id)
        except Todo.DoesNotExist as e:
            raise TodoNotFoundError(f"Todo {todo_id} not found") from e

        if todo.user_id != user.id:
            raise TodoAccessDeniedError("Cannot access another user's todo")

        return todo

    def list_todos_for_user(
        self,
        user: User,
        *,
        completed: bool | None = None,
    ) -> list[Todo]:
        """List all todos for a user.

        Args:
            user: The user whose todos to list.
            completed: Optional filter for completion status.

        Returns:
            List of Todo instances.
        """
        queryset = Todo.objects.filter(user=user)

        if completed is not None:
            queryset = queryset.filter(completed=completed)

        return list(queryset)

    @transaction.atomic
    def create_todo(
        self,
        user: User,
        *,
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
        return Todo.objects.create(
            user=user,
            title=title,
            description=description,
        )

    @transaction.atomic
    def update_todo(
        self,
        todo_id: int,
        user: User,
        *,
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
        todo = self.get_todo_by_id(todo_id, user)

        if title is not None:
            todo.title = title
        if description is not None:
            todo.description = description
        if completed is not None:
            todo.completed = completed

        todo.save()
        return todo

    @transaction.atomic
    def delete_todo(self, todo_id: int, user: User) -> None:
        """Delete a todo item.

        Args:
            todo_id: The todo's primary key.
            user: The requesting user.

        Raises:
            TodoNotFoundError: If the todo doesn't exist.
            TodoAccessDeniedError: If the todo belongs to another user.
        """
        todo = self.get_todo_by_id(todo_id, user)
        todo.delete()

    def mark_completed(self, todo_id: int, user: User) -> Todo:
        """Mark a todo as completed.

        Args:
            todo_id: The todo's primary key.
            user: The requesting user.

        Returns:
            The updated Todo instance.
        """
        return self.update_todo(todo_id, user, completed=True)

    def mark_incomplete(self, todo_id: int, user: User) -> Todo:
        """Mark a todo as incomplete.

        Args:
            todo_id: The todo's primary key.
            user: The requesting user.

        Returns:
            The updated Todo instance.
        """
        return self.update_todo(todo_id, user, completed=False)

    @transaction.atomic
    def delete_completed_todos(self, user: User) -> int:
        """Delete all completed todos for a user.

        Args:
            user: The user whose completed todos to delete.

        Returns:
            Number of todos deleted.
        """
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
4. **Transaction Management**: `@transaction.atomic` ensures data integrity

### Key Patterns in This Service

**Domain Exceptions**: `TodoNotFoundError` and `TodoAccessDeniedError` communicate specific errors that controllers can map to HTTP responses.

**Ownership Checks**: `get_todo_by_id` verifies the user owns the todo before returning it.

**Type Hints**: All methods have complete type annotations for `mypy --strict`.

**Docstrings**: Google-style docstrings document args, returns, and raises.

## Verification

Test the service in a Django shell:

```bash
uv run python src/manage.py shell
```

```python
from core.user.models import User
from core.todo.services import TodoService

# Get or create a test user
user = User.objects.first()
if not user:
    user = User.objects.create_user("testuser", "test@example.com", "password")

# Create a service instance
service = TodoService()

# Create a todo
todo = service.create_todo(user, title="Learn Fast Django", description="Complete the tutorial")
print(f"Created: {todo.title}")

# List todos
todos = service.list_todos_for_user(user)
print(f"User has {len(todos)} todos")

# Mark complete
service.mark_completed(todo.id, user)
print(f"Completed: {todo.completed}")
```

## Summary

You've created:

- A `Todo` Django model with user ownership
- A `TodoService` with CRUD operations
- Domain exceptions for error handling
- Database indexes for performance

## Next Step

In [Step 2: IoC Registration](02-ioc-registration.md), you'll learn how the IoC container automatically wires dependencies.
