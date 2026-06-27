# Add Celery Task

Create background tasks for asynchronous processing.

## Goal

Add a new Celery task for background processing.

## Prerequisites

- Celery worker running (`make celery-dev`)
- Understanding of [Controller Pattern](../concepts/controller-pattern.md)

## Checklist

- [ ] Create task controller
- [ ] Add task name to `TaskName` enum
- [ ] Register controller in factory
- [ ] Add task to registry (optional, for type-safe access)
- [ ] Write tests

## Step-by-Step

### 1. Create Task Controller

Create `src/modern_python_template/core/email/delivery/celery/send_email.py`:

```python
# src/modern_python_template/core/email/delivery/celery/send_email.py
from dataclasses import dataclass

from celery import Celery
from diwire import Injected

from modern_python_template.core.email.services import EmailService
from modern_python_template.foundation.delivery.celery.schemas import BaseCelerySchema
from modern_python_template.core.user.use_cases import UserUseCase
from modern_python_template.infrastructure.celery.controllers import BaseCeleryTaskController

SEND_EMAIL_TASK_NAME = "email.send"


class SendEmailResultSchema(BaseCelerySchema):
    success: bool
    message_id: str | None


@dataclass(kw_only=True)
class SendEmailTaskController(BaseCeleryTaskController):
    """Task controller for sending emails."""

    _email_service: Injected[EmailService]
    _user_use_case: Injected[UserUseCase]

    def register(self, registry: Celery) -> None:
        self._register_task(registry, name=SEND_EMAIL_TASK_NAME, handler=self.send_email)

    async def send_email(
        self,
        user_id: int,
        subject: str,
        body: str,
    ) -> SendEmailResultSchema:
        """Send an email to a user.

        Args:
            user_id: The recipient user's ID.
            subject: Email subject line.
            body: Email body content.

        Returns:
            Result containing success status and message ID.
        """
        user = await self._user_use_case.get_user_by_id(user_id=user_id)

        try:
            message_id = await self._email_service.send(
                to=user.email,
                subject=subject,
                body=body,
            )
            return SendEmailResultSchema(success=True, message_id=message_id)
        except Exception:
            return SendEmailResultSchema(success=False, message_id=None)
```

### 2. Add Task Name to the Registry

Edit `src/modern_python_template/entrypoints/celery/registry.py`:

```python
# src/modern_python_template/entrypoints/celery/registry.py
from enum import StrEnum

from modern_python_template.core.email.delivery.celery.send_email import SEND_EMAIL_TASK_NAME
from modern_python_template.core.health.delivery.celery.tasks import PING_TASK_NAME


class TaskName(StrEnum):
    PING = PING_TASK_NAME
    SEND_EMAIL = SEND_EMAIL_TASK_NAME
```

This keeps domain task modules independent from the entrypoint registry.

### 3. Register Task Controller

Edit `src/modern_python_template/entrypoints/celery/factories.py`:

```python
# src/modern_python_template/entrypoints/celery/factories.py
# Add import
from modern_python_template.core.email.delivery.celery.send_email import SendEmailTaskController


@dataclass(kw_only=True)
class TasksRegistryFactory(BaseFactory):
    _celery_app_factory: Injected[CeleryAppFactory]
    _ping_controller: Injected[PingTaskController]
    _send_email_controller: Injected[SendEmailTaskController]  # Add as field

    _instance: TasksRegistry | None = field(default=None, init=False)

    def __call__(self) -> TasksRegistry:
        if self._instance is not None:
            return self._instance

        celery_app = self._celery_app_factory()
        registry = TasksRegistry(_celery_app=celery_app)
        self._ping_controller.register(celery_app)
        self._send_email_controller.register(celery_app)  # Register it

        self._instance = registry
        return self._instance
```

Controllers are declared as dataclass fields and auto-resolved by the IoC container.

### 4. Add to Registry (Optional)

For type-safe task access, add to `TasksRegistry`:

```python
# src/modern_python_template/entrypoints/celery/registry.py
from modern_python_template.infrastructure.celery.registry import BaseTasksRegistry, CeleryTask


class TasksRegistry(BaseTasksRegistry):
    @property
    def ping(self) -> CeleryTask[[], PingResultSchema]:
        return self._get_task_by_name(TaskName.PING)

    @property
    def send_email(self) -> CeleryTask[[int, str, str], SendEmailResultSchema]:  # Add this
        return self._get_task_by_name(TaskName.SEND_EMAIL)
```

### 5. Call the Task

Inject `TasksRegistry` into a use case or service. Controllers should keep
calling use cases/services and should not enqueue tasks directly.

```python
@dataclass(kw_only=True)
class UserUseCase(BaseUseCase):
    _tasks_registry: Injected[TasksRegistry]

    async def create_user(self, *, data: CreateUserDTO) -> User:
        user = await self._create_user(data=data)

        # Queue welcome email
        await self._tasks_registry.send_email.adelay(
            user_id=user.id,
            subject="Welcome!",
            body="Thanks for signing up.",
        )

        return user
```

### 6. Schedule the Task (Optional)

For periodic tasks, add to beat schedule in `src/modern_python_template/entrypoints/celery/factories.py`:

```python
from celery.schedules import crontab


class CeleryAppFactory(BaseFactory):
    def __call__(self) -> Celery:
        celery_app = Celery(...)

        celery_app.conf.beat_schedule = {
            "ping-every-minute": {
                "task": TaskName.PING,
                "schedule": 60.0,
            },
            # Add scheduled task
            "send-daily-digest": {
                "task": TaskName.SEND_EMAIL,
                "schedule": crontab(hour=9, minute=0),  # 9:00 AM daily
                "args": [None, "Daily Digest", "Your daily summary..."],
            },
        }

        return celery_app
```

Start beat scheduler:

```bash
make celery-beat-dev
```

### 7. Write Tests

```python
# tests/integration/core/email/delivery/celery/test_send_email.py
import asyncio
from unittest.mock import AsyncMock

import pytest
from diwire import Container

from modern_python_template.core.email.services import EmailService
from modern_python_template.core.user.models import User
from tests.integration.factories import (
    TestCeleryWorkerFactory,
    TestTasksRegistryFactory,
    TestUserFactory,
)


@pytest.fixture
def mock_email_service(container: Container) -> AsyncMock:
    mock = AsyncMock(spec=EmailService)
    mock.send.return_value = "msg_123"
    container.add_instance(mock, provides=EmailService)
    return mock


@pytest.mark.django_db(transaction=True)
class TestSendEmailTask:
    def test_send_email_success(
        self,
        celery_worker_factory: TestCeleryWorkerFactory,
        tasks_registry_factory: TestTasksRegistryFactory,
        user_factory: TestUserFactory,
        mock_email_service: AsyncMock,
    ) -> None:
        user = user_factory(email="test@example.com")
        registry = tasks_registry_factory()

        with celery_worker_factory():
            result = asyncio.run(
                registry.send_email.adelay(
                    user_id=user.id,
                    subject="Test",
                    body="Hello",
                ),
            )
            task_result = asyncio.run(result.aget(timeout=10))

        assert task_result["success"] is True
        assert task_result["message_id"] == "msg_123"
        mock_email_service.send.assert_awaited_once_with(
            to="test@example.com",
            subject="Test",
            body="Hello",
        )
```

## Task Best Practices

### Pass IDs, Not Objects

```python
# Good - serializable
async def send_email(self, user_id: int, ...) -> SendEmailResultSchema:
    user = await self._user_use_case.get_user_by_id(user_id=user_id)

# Bad - Django models aren't serializable
async def send_email(self, user: User, ...) -> SendEmailResultSchema:
    ...
```

### Make Tasks Idempotent

```python
async def process_order(self, order_id: int) -> ProcessResultSchema:
    order = await self._order_service.get_order_by_id(order_id=order_id)

    # Check if already processed
    if order.status == OrderStatus.PROCESSED:
        return ProcessResultSchema(already_processed=True)

    # Process order
    ...
```

### Handle Failures Gracefully

```python
async def send_notification(self, user_id: int) -> NotifyResultSchema:
    try:
        await self._push_service.send(user_id, message)
        return NotifyResultSchema(success=True)
    except PushServiceError as e:
        # Log error but don't crash
        logfire.error("Push failed", user_id=user_id, error=str(e))
        return NotifyResultSchema(success=False, error=str(e))
```

### Use BaseCelerySchema for Results

```python
from modern_python_template.foundation.delivery.celery.schemas import BaseCelerySchema


class ProcessResultSchema(BaseCelerySchema):
    success: bool
    items_processed: int
    errors: list[str]
```

## File Summary

| Action | File |
|--------|------|
| Modify | `src/modern_python_template/entrypoints/celery/registry.py` |
| Create | `src/modern_python_template/core/email/delivery/celery/send_email.py` |
| Modify | `src/modern_python_template/entrypoints/celery/factories.py` |
| Create | `tests/integration/core/email/delivery/celery/test_send_email.py` |

## Verification

1. Start Celery worker: `make celery-dev`
2. Trigger task in shell:

```python
from modern_python_template.ioc.container import get_container
from modern_python_template.entrypoints.celery.registry import TasksRegistry

container = get_container()
registry = container.resolve(TasksRegistry)
result = registry.send_email.delay(user_id=1, subject="Test", body="Hello")
print(result.get(timeout=10))
```

Use `.adelay()` instead of `.delay()` when enqueueing from async code. If async
code needs a result, use `await result.aget(timeout=...)`, and use
`await result.aforget()` when the result backend state should be discarded.
