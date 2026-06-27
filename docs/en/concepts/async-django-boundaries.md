# Async Django Boundaries

FastAPI and Celery delivery are async-first. Controllers inherit
`BaseAsyncController` or `BaseCeleryTaskController`, public use-case and service
methods are async where they are called from delivery flows, and Django
connection cleanup is handled at the FastAPI request boundary or Celery task
bridge.

## The rule

Async code may do non-transactional ORM reads with Django's async ORM methods:

```python
# src/modern_python_template/core/user/use_cases.py
from modern_python_template.core.user.models import User


async def get_user_by_id(self, *, user_id: int) -> User | None:
    return await User.objects.filter(id=user_id).afirst()
```

Django transactions stay sync and go through the injected `TransactionFactory`.
If a workflow needs a transaction, keep it in a small sync method and call it
from async orchestration with `sync_to_async(..., thread_sensitive=True)`:

```python
# src/modern_python_template/core/user/use_cases.py
from asgiref.sync import sync_to_async
from django.contrib.auth.hashers import make_password
from diwire import Injected

from modern_python_template.core.user.dtos import CreateUserDTO
from modern_python_template.core.user.models import User
from modern_python_template.foundation.transactions import TransactionFactory
from modern_python_template.foundation.use_cases import BaseUseCase


class UserUseCase(BaseUseCase):
    _transaction_factory: Injected[TransactionFactory]

    async def create_user(self, *, data: CreateUserDTO) -> User:
        return await sync_to_async(
            self._create_user_transactionally,
            thread_sensitive=True,
        )(data=data)

    def _create_user_transactionally(self, *, data: CreateUserDTO) -> User:
        password = make_password(data.password)

        with self._transaction_factory(span_name="create user"):
            return User.objects.create(..., password=password)
```

Never put `await` inside a Django transaction. Do async/network work before or
after the transaction, or use an outbox/job table when the workflow needs
reliable external side effects.

Django password hashing, password validation, and `check_password()` are sync
CPU work. Keep them in a sync use-case/service method and call that method with
`sync_to_async(..., thread_sensitive=True)` instead of running them on the event
loop. Also do password hashing and validation before opening the transaction so
the database transaction does not sit idle while CPU work runs.

## Connection handling

FastAPI and Celery run without Django's request handler, so the app adds Django
connection cleanup middleware around each HTTP request and WebSocket connection,
and wraps each Celery task handler with the same connection-boundary cleanup.
The middleware also creates an `asgiref.sync.ThreadSensitiveContext`, matching
Django's ASGI handler, so thread-sensitive ORM work for one ASGI connection
shares one worker thread and connection lifecycle.

`DATABASE_CONN_MAX_AGE` defaults to `0` for ASGI; use database/backend pooling
rather than Django persistent connections. Docker routes application traffic
through PgBouncer in transaction pooling mode, so
`DATABASE_DISABLE_SERVER_SIDE_CURSORS` defaults to `true`.
