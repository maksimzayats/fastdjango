# Step 4: Celery Tasks

Add background task processing for todo cleanup.

## What You'll Build

- Celery task controller for cleaning completed todos
- Task registration and naming
- Scheduled task with Celery Beat

## Files to Create/Modify

| Action | File Path |
|--------|-----------|
| Create | `src/delivery/tasks/tasks/todo_cleanup.py` |
| Modify | `src/delivery/tasks/registry.py` |
| Modify | `src/delivery/tasks/factories.py` |

## Concept Reference

> **See also:** [Controller Pattern concept](../concepts/controller-pattern.md) for how Celery tasks use the same pattern as HTTP controllers.

## Step 1: Create the Task Controller

Celery tasks follow the same controller pattern as HTTP endpoints. Create `src/delivery/tasks/tasks/todo_cleanup.py`:

```python
# src/delivery/tasks/tasks/todo_cleanup.py
from dataclasses import dataclass
from typing import TypedDict

from celery import Celery

from core.todo.services import TodoService
from core.user.services.user import UserService
from delivery.tasks.registry import TaskName
from infrastructure.delivery.controllers import Controller


class CleanupResult(TypedDict):
    """Result of the cleanup task."""

    users_processed: int
    todos_deleted: int


@dataclass(kw_only=True)
class TodoCleanupTaskController(Controller):
    """Task controller for cleaning up completed todos."""

    _todo_service: TodoService
    _user_service: UserService

    def register(self, registry: Celery) -> None:
        """Register the task with Celery."""
        registry.task(name=TaskName.TODO_CLEANUP)(self.cleanup_completed_todos)

    def cleanup_completed_todos(self) -> CleanupResult:
        """Delete all completed todos for all users.

        This task is designed to run on a schedule (e.g., daily)
        to clean up completed todos that are no longer needed.

        Returns:
            Dictionary with counts of users processed and todos deleted.
        """
        users = self._user_service.list_all_users()

        total_deleted = 0
        for user in users:
            deleted_count = self._todo_service.delete_completed_todos(user)
            total_deleted += deleted_count

        return CleanupResult(
            users_processed=len(users),
            todos_deleted=total_deleted,
        )
```

## Step 2: Add User List Method to UserService

The cleanup task needs to iterate over all users. Add this method to `src/core/user/services/user.py`:

```python
# Add to UserService class in src/core/user/services/user.py
def list_all_users(self) -> list[User]:
    """List all active users.

    Returns:
        List of active User instances.
    """
    return list(User.objects.filter(is_active=True))
```

## Step 3: Register the Task Name

Add the task name to the registry in `src/delivery/tasks/registry.py`:

```python
# src/delivery/tasks/registry.py
from enum import StrEnum


class TaskName(StrEnum):
    """Enumeration of all task names."""

    PING = "ping"
    TODO_CLEANUP = "todo.cleanup"  # Add this line
```

Also add the task property to `TasksRegistry`:

```python
# In the TasksRegistry class
@property
def todo_cleanup(self) -> Task:
    return self._celery_app.tasks[TaskName.TODO_CLEANUP]
```

## Step 4: Register the Task Controller

Modify `src/delivery/tasks/factories.py` to register the new task controller:

```python
# src/delivery/tasks/factories.py
# Add this import at the top
from delivery.tasks.tasks.todo_cleanup import TodoCleanupTaskController


@dataclass(kw_only=True)
class TasksRegistryFactory:
    _celery_app_factory: CeleryAppFactory
    _ping_controller: PingTaskController
    _todo_cleanup_controller: TodoCleanupTaskController  # Add this field
    _instance: TasksRegistry | None = field(default=None, init=False)

    def __call__(self) -> TasksRegistry:
        if self._instance is not None:
            return self._instance

        celery_app = self._celery_app_factory()
        registry = TasksRegistry(_celery_app=celery_app)
        self._ping_controller.register(celery_app)
        self._todo_cleanup_controller.register(celery_app)  # Register it

        self._instance = registry
        return self._instance
```

Controllers are declared as dataclass fields and auto-resolved by the IoC container.

## Step 5: Schedule the Task (Optional)

To run the cleanup task automatically, add it to the Celery Beat schedule. In `src/delivery/tasks/factories.py`, modify the beat schedule in `CeleryAppFactory`:

```python
# In CeleryAppFactory.__call__ method, update beat_schedule:
celery_app.conf.beat_schedule = {
    "ping-every-minute": {
        "task": TaskName.PING,
        "schedule": 60.0,  # Every 60 seconds
    },
    "cleanup-completed-todos-daily": {
        "task": TaskName.TODO_CLEANUP,
        "schedule": crontab(hour=2, minute=0),  # 2:00 AM daily
    },
}
```

Add the import at the top of the file:

```python
from celery.schedules import crontab
```

## Understanding the Task Pattern

### Task Controller Structure

```python
@dataclass(kw_only=True)
class MyTaskController(Controller):
    # Dependencies injected automatically
    _my_service: MyService

    def register(self, registry: Celery) -> None:
        # Register task with Celery
        registry.task(name=TaskName.MY_TASK)(self.my_task_method)

    def my_task_method(self, arg1: str) -> dict:
        # Task logic here
        return {"status": "done"}
```

!!! note "Dataclass decorator"
    Add `@dataclass(kw_only=True)` only when your controller has dependencies to inject. Simple controllers without dependencies (like `PingTaskController`) don't need it because they inherit from the base `Controller` class which already uses `@dataclass(kw_only=True)`.

### Task Naming Convention

Use dotted names for task organization:

- `ping` - Simple utility tasks
- `todo.cleanup` - Domain-specific tasks
- `user.notifications.send` - Nested domain tasks

### Type-Safe Task Invocation

Use the task registry for type-safe calls:

```python
from delivery.tasks.registry import TasksRegistry

# Get registry (typically injected)
registry = container.resolve(TasksRegistry)

# Call task asynchronously
result = registry.todo_cleanup.delay()

# Wait for result (in tests)
cleanup_result = result.get(timeout=30)
```

## Verification

### Manual Task Execution

1. Start the Celery worker:

```bash
make celery-dev
```

2. In another terminal, trigger the task:

```python
# Using Django shell
uv run python src/manage.py shell
```

```python
from ioc.container import ContainerFactory
from delivery.tasks.registry import TasksRegistry

# Create container and get registry
container = ContainerFactory()()
registry = container.resolve(TasksRegistry)

# Trigger the cleanup task
result = registry.todo_cleanup.delay()

# Wait for result
print(result.get(timeout=30))
```

### Test Scheduled Execution

1. Start Celery Beat:

```bash
make celery-beat-dev
```

2. Check the logs for scheduled task execution

## Task Best Practices

### Do: Keep Tasks Idempotent

Tasks should be safe to retry:

```python
def cleanup_completed_todos(self) -> CleanupResult:
    # This is idempotent - running it twice doesn't cause issues
    deleted_count = self._todo_service.delete_completed_todos(user)
    return {"deleted": deleted_count}
```

### Do: Return Serializable Results

Use `TypedDict` or simple dicts:

```python
class CleanupResult(TypedDict):
    users_processed: int
    todos_deleted: int
```

### Don't: Pass Django Models to Tasks

```python
# Bad - Django models aren't serializable
def process_user(self, user: User) -> None:
    ...

# Good - Pass IDs instead
def process_user(self, user_id: int) -> None:
    user = self._user_service.get_user_by_id(user_id)
    ...
```

### Do: Handle Failures Gracefully

```python
def cleanup_completed_todos(self) -> CleanupResult:
    errors = []
    for user in users:
        try:
            self._todo_service.delete_completed_todos(user)
        except Exception as e:
            errors.append({"user_id": user.id, "error": str(e)})

    return {"errors": errors, "users_processed": len(users)}
```

## Summary

You've created:

- A Celery task controller following the same pattern as HTTP controllers
- Task registration with enum-based naming
- Type-safe task invocation via the registry
- Optional scheduled execution with Celery Beat

## Next Step

In [Step 5: Observability](05-observability.md), you'll add logging and tracing to monitor your application.
