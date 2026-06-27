# Step 4: Celery Tasks

Add background task processing for todo cleanup.

## What You'll Build

- Celery task controller for cleaning completed todos
- Task registration and naming
- Scheduled task with Celery Beat

## Files to Create/Modify

| Action | File Path |
|--------|-----------|
| Create | `src/modern_python_template/core/todo/delivery/celery/todo_cleanup.py` |
| Modify | `src/modern_python_template/entrypoints/celery/registry.py` |
| Modify | `src/modern_python_template/entrypoints/celery/factories.py` |

## Concept Reference

> **See also:** [Controller Pattern concept](../concepts/controller-pattern.md) for how Celery tasks use the same pattern as HTTP controllers.

## Step 1: Create the Task Controller

Celery tasks follow the same controller pattern as HTTP endpoints. Create `src/modern_python_template/core/todo/delivery/celery/todo_cleanup.py`:

```python
# src/modern_python_template/core/todo/delivery/celery/todo_cleanup.py
from dataclasses import dataclass

from celery import Celery
from diwire import Injected

from modern_python_template.foundation.delivery.celery.schemas import BaseCelerySchema
from modern_python_template.core.todo.services import TodoService
from modern_python_template.core.user.use_cases import UserUseCase
from modern_python_template.infrastructure.celery.controllers import BaseCeleryTaskController

TODO_CLEANUP_TASK_NAME = "todo.cleanup"


class CleanupResultSchema(BaseCelerySchema):
    """Result of the cleanup task."""

    users_processed: int
    todos_deleted: int


@dataclass(kw_only=True)
class TodoCleanupTaskController(BaseCeleryTaskController):
    """Task controller for cleaning up completed todos."""

    _todo_service: Injected[TodoService]
    _user_use_case: Injected[UserUseCase]

    def register(self, registry: Celery) -> None:
        """Register the task with Celery."""
        self._register_task(
            registry,
            name=TODO_CLEANUP_TASK_NAME,
            handler=self.cleanup_completed_todos,
        )

    async def cleanup_completed_todos(self) -> CleanupResultSchema:
        """Delete all completed todos for all users.

        This task is designed to run on a schedule (e.g., daily)
        to clean up completed todos that are no longer needed.

        Returns:
            Dictionary with counts of users processed and todos deleted.
        """
        users = await self._user_use_case.list_all_users()

        total_deleted = 0
        for user in users:
            deleted_count = await self._todo_service.delete_completed_todos(user=user)
            total_deleted += deleted_count

        return CleanupResultSchema(
            users_processed=len(users),
            todos_deleted=total_deleted,
        )
```

## Step 2: Add User List Method to UserUseCase

The cleanup task needs to iterate over all users. Add the import near the top of
`src/modern_python_template/core/user/use_cases.py`:

```python
# src/modern_python_template/core/user/use_cases.py
from asgiref.sync import sync_to_async
```

Then add the methods to `UserUseCase`:

```python
# Add to UserUseCase class in src/modern_python_template/core/user/use_cases.py
async def list_all_users(self) -> list[User]:
    """List all active users.

    Returns:
        List of active User instances.
    """
    return await sync_to_async(self._list_all_users, thread_sensitive=True)()


def _list_all_users(self) -> list[User]:
    return list(User.objects.filter(is_active=True))
```

## Step 3: Register the Task Name

Add the task name to the registry in `src/modern_python_template/entrypoints/celery/registry.py`:

```python
# src/modern_python_template/entrypoints/celery/registry.py
from enum import StrEnum

from modern_python_template.core.health.delivery.celery.tasks import PING_TASK_NAME
from modern_python_template.core.todo.delivery.celery.todo_cleanup import TODO_CLEANUP_TASK_NAME


class TaskName(StrEnum):
    """Enumeration of all task names."""

    PING = PING_TASK_NAME
    TODO_CLEANUP = TODO_CLEANUP_TASK_NAME  # Add this line
```

Also add the task property to `TasksRegistry`:

```python
# In the TasksRegistry class
@property
def todo_cleanup(self) -> CeleryTask[[], CleanupResultSchema]:
    return self._get_task_by_name(TaskName.TODO_CLEANUP)
```

## Step 4: Register the Task Controller

Modify `src/modern_python_template/entrypoints/celery/factories.py` to register the new task controller:

```python
# src/modern_python_template/entrypoints/celery/factories.py
# Add this import at the top
from modern_python_template.core.todo.delivery.celery.todo_cleanup import TodoCleanupTaskController


@dataclass(kw_only=True)
class TasksRegistryFactory(BaseFactory):
    _celery_app_factory: Injected[CeleryAppFactory]
    _ping_controller: Injected[PingTaskController]
    _todo_cleanup_controller: Injected[TodoCleanupTaskController]  # Add this field

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

To run the cleanup task automatically, add it to the Celery Beat schedule. In `src/modern_python_template/entrypoints/celery/factories.py`, modify the beat schedule in `CeleryAppFactory`:

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
MY_TASK_NAME = "my.task"


@dataclass(kw_only=True)
class MyTaskController(BaseCeleryTaskController):
    # Dependencies injected automatically
    _my_service: Injected[MyService]

    def register(self, registry: Celery) -> None:
        # Register task with Celery
        self._register_task(registry, name=MY_TASK_NAME, handler=self.my_task_method)

    async def my_task_method(self, arg1: str) -> dict:
        # Task logic here
        return {"status": "done"}
```

!!! note "Dataclass decorator"
    Concrete task controllers use `@dataclass(kw_only=True)` even when they do not have dependencies. This keeps the injectable class shape consistent.

### Task Naming Convention

Use dotted names for task organization:

- `ping` - Simple utility tasks
- `todo.cleanup` - Domain-specific tasks
- `user.notifications.send` - Nested domain tasks

### Type-Safe Task Invocation

Use the task registry for type-safe calls:

```python
from modern_python_template.entrypoints.celery.registry import TasksRegistry

# Get registry manually in shell examples.
# In application code, inject TasksRegistry into use cases or services.
registry = container.resolve(TasksRegistry)

# Call task from sync code
result = registry.todo_cleanup.delay()

# Call task from async code
result = await registry.todo_cleanup.adelay()

# Wait for result from async code
cleanup_result = await result.aget(timeout=30)
```

## Verification

### Manual Task Execution

1. Start the Celery worker:

```bash
make celery-dev
```

2. In another terminal, trigger the task:

```bash
# management/manage.py
uv run python management/manage.py shell
```

```python
from modern_python_template.ioc.container import get_container
from modern_python_template.entrypoints.celery.registry import TasksRegistry

# Create container and get registry
container = get_container()
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
async def cleanup_completed_todos(self) -> CleanupResultSchema:
    # This is idempotent - running it twice doesn't cause issues
    deleted_count = await self._todo_service.delete_completed_todos(user=user)
    return {"deleted": deleted_count}
```

### Do: Return Serializable Results

Use `BaseCelerySchema` or simple dicts:

```python
from modern_python_template.foundation.delivery.celery.schemas import BaseCelerySchema


class CleanupResultSchema(BaseCelerySchema):
    users_processed: int
    todos_deleted: int
```

### Don't: Pass Django Models to Tasks

```python
# Bad - Django models aren't serializable
async def process_user(self, user: User) -> None:
    ...

# Good - Pass IDs instead
async def process_user(self, user_id: int) -> None:
    user = await self._user_use_case.get_user_by_id(user_id=user_id)
    ...
```

### Do: Handle Failures Gracefully

```python
async def cleanup_completed_todos(self) -> CleanupResultSchema:
    errors = []
    for user in users:
        try:
            await self._todo_service.delete_completed_todos(user=user)
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
