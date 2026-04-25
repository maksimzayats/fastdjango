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

Create `src/fastdjango/core/email/delivery/celery/send_email.py`:

```python
# src/fastdjango/core/email/delivery/celery/send_email.py
from dataclasses import dataclass

from celery import Celery

from fastdjango.core.email.services import EmailService
from fastdjango.foundation.delivery.celery.schemas import BaseCelerySchema
from fastdjango.core.user.use_cases import UserUseCase
from fastdjango.foundation.delivery.controllers import BaseController

SEND_EMAIL_TASK_NAME = "email.send"


class SendEmailResultSchema(BaseCelerySchema):
    success: bool
    message_id: str | None


@dataclass(kw_only=True)
class SendEmailTaskController(BaseController):
    """Task controller for sending emails."""

    _email_service: EmailService
    _user_use_case: UserUseCase

    def register(self, registry: Celery) -> None:
        registry.task(name=SEND_EMAIL_TASK_NAME)(self.send_email)

    def send_email(
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
        user = self._user_use_case.get_user_by_id(user_id)

        try:
            message_id = self._email_service.send(
                to=user.email,
                subject=subject,
                body=body,
            )
            return SendEmailResultSchema(success=True, message_id=message_id)
        except Exception:
            return SendEmailResultSchema(success=False, message_id=None)
```

### 2. Add Task Name to the Registry

Edit `src/fastdjango/entrypoints/celery/registry.py`:

```python
# src/fastdjango/entrypoints/celery/registry.py
from enum import StrEnum

from fastdjango.core.email.delivery.celery.send_email import SEND_EMAIL_TASK_NAME
from fastdjango.core.health.delivery.celery.tasks import PING_TASK_NAME


class TaskName(StrEnum):
    PING = PING_TASK_NAME
    SEND_EMAIL = SEND_EMAIL_TASK_NAME
```

This keeps domain task modules independent from the entrypoint registry.

### 3. Register Task Controller

Edit `src/fastdjango/entrypoints/celery/factories.py`:

```python
# src/fastdjango/entrypoints/celery/factories.py
# Add import
from fastdjango.core.email.delivery.celery.send_email import SendEmailTaskController


@dataclass(kw_only=True)
class TasksRegistryFactory(BaseFactory):
    _celery_app_factory: CeleryAppFactory
    _ping_controller: PingTaskController
    _send_email_controller: SendEmailTaskController  # Add as field
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
# src/fastdjango/entrypoints/celery/registry.py
from celery import Task

from fastdjango.infrastructure.celery.registry import BaseTasksRegistry


class TasksRegistry(BaseTasksRegistry):
    @property
    def ping(self) -> Task:
        return self._get_task_by_name(TaskName.PING)

    @property
    def send_email(self) -> Task:  # Add this
        return self._get_task_by_name(TaskName.SEND_EMAIL)
```

### 5. Call the Task

From HTTP controllers or other services:

```python
@dataclass(kw_only=True)
class UserController(BaseTransactionController):
    _tasks_registry: TasksRegistry

    def create_user(self, body: CreateUserSchema) -> UserSchema:
        user = self._user_use_case.create_user(...)

        # Queue welcome email
        self._tasks_registry.send_email.delay(
            user_id=user.id,
            subject="Welcome!",
            body="Thanks for signing up.",
        )

        return UserSchema.model_validate(user, from_attributes=True)
```

### 6. Schedule the Task (Optional)

For periodic tasks, add to beat schedule in `src/fastdjango/entrypoints/celery/factories.py`:

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
# tests/integration/celery/test_send_email.py
from unittest.mock import MagicMock

import pytest

from fastdjango.core.email.services import EmailService
from fastdjango.core.user.models import User
from tests.integration.factories import (
    TestCeleryWorkerFactory,
    TestTasksRegistryFactory,
    TestUserFactory,
)


@pytest.fixture
def mock_email_service(container: Container) -> MagicMock:
    mock = MagicMock(spec=EmailService)
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
        mock_email_service: MagicMock,
    ) -> None:
        user = user_factory(email="test@example.com")
        registry = tasks_registry_factory()

        with celery_worker_factory():
            result = registry.send_email.delay(
                user_id=user.id,
                subject="Test",
                body="Hello",
            ).get(timeout=10)

        assert result["success"] is True
        assert result["message_id"] == "msg_123"
        mock_email_service.send.assert_called_once_with(
            to="test@example.com",
            subject="Test",
            body="Hello",
        )
```

## Task Best Practices

### Pass IDs, Not Objects

```python
# Good - serializable
def send_email(self, user_id: int, ...) -> SendEmailResultSchema:
    user = self._user_use_case.get_user_by_id(user_id)

# Bad - Django models aren't serializable
def send_email(self, user: User, ...) -> SendEmailResultSchema:
    ...
```

### Make Tasks Idempotent

```python
def process_order(self, order_id: int) -> ProcessResultSchema:
    order = self._order_service.get_order_by_id(order_id)

    # Check if already processed
    if order.status == OrderStatus.PROCESSED:
        return ProcessResultSchema(already_processed=True)

    # Process order
    ...
```

### Handle Failures Gracefully

```python
def send_notification(self, user_id: int) -> NotifyResultSchema:
    try:
        self._push_service.send(user_id, message)
        return NotifyResultSchema(success=True)
    except PushServiceError as e:
        # Log error but don't crash
        logfire.error("Push failed", user_id=user_id, error=str(e))
        return NotifyResultSchema(success=False, error=str(e))
```

### Use BaseCelerySchema for Results

```python
from fastdjango.foundation.delivery.celery.schemas import BaseCelerySchema


class ProcessResultSchema(BaseCelerySchema):
    success: bool
    items_processed: int
    errors: list[str]
```

## File Summary

| Action | File |
|--------|------|
| Modify | `src/fastdjango/entrypoints/celery/registry.py` |
| Create | `src/fastdjango/core/email/delivery/celery/send_email.py` |
| Modify | `src/fastdjango/entrypoints/celery/factories.py` |
| Create | `tests/integration/celery/test_send_email.py` |

## Verification

1. Start Celery worker: `make celery-dev`
2. Trigger task in shell:

```python
from fastdjango.ioc.container import get_container
from fastdjango.entrypoints.celery.factories import TasksRegistryFactory

container = get_container()
registry = container.resolve(TasksRegistryFactory)()
result = registry.send_email.delay(user_id=1, subject="Test", body="Hello")
print(result.get(timeout=10))
```
