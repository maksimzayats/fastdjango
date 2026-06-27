from abc import ABC
from collections.abc import Awaitable, Callable
from functools import wraps

from asgiref.sync import async_to_sync
from celery import Celery, Task
from django.db import close_old_connections

from modern_python_template.foundation.delivery.controllers import BaseAsyncController


class BaseCeleryTaskController(BaseAsyncController, ABC):
    def _register_task[**P, R](
        self,
        registry: Celery,
        *,
        name: str,
        handler: Callable[P, Awaitable[R]],
    ) -> Task[P, R]:
        sync_handler = async_to_sync(handler)

        @wraps(handler)
        def task(*args: P.args, **kwargs: P.kwargs) -> R:
            # Celery does not run through Django's request lifecycle, so keep the
            # worker-side database connection boundary explicit for each task.
            close_old_connections()
            try:
                return sync_handler(*args, **kwargs)
            finally:
                close_old_connections()

        return registry.task(name=name)(task)
