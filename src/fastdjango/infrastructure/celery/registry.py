import asyncio
from dataclasses import dataclass
from typing import Any

from celery import Celery, Task
from celery.result import AsyncResult


class TaskNotFoundError(Exception):
    pass


@dataclass(kw_only=True)
class CeleryTaskResult[R]:
    result: AsyncResult[R]

    @property
    def raw(self) -> AsyncResult[R]:
        return self.result

    def get(self, *, timeout: float | None = None) -> R:
        return self.result.get(timeout=timeout)

    async def aget(self, *, timeout: float | None = None) -> R:  # noqa: ASYNC109
        return await asyncio.to_thread(self.get, timeout=timeout)

    def forget(self) -> None:
        self.result.forget()

    async def aforget(self, *, timeout: float | None = None) -> None:  # noqa: ASYNC109
        forget = asyncio.to_thread(self.forget)

        if timeout is None:
            await forget
            return

        await asyncio.wait_for(forget, timeout=timeout)


@dataclass(kw_only=True)
class CeleryTask[**P, R]:
    task: Task[P, R]

    @property
    def name(self) -> str:
        return self.task.name

    @property
    def raw(self) -> Task[P, R]:
        return self.task

    def delay(self, *args: P.args, **kwargs: P.kwargs) -> CeleryTaskResult[R]:
        return CeleryTaskResult(result=self.task.delay(*args, **kwargs))

    async def adelay(self, *args: P.args, **kwargs: P.kwargs) -> CeleryTaskResult[R]:
        return await asyncio.to_thread(self.delay, *args, **kwargs)

    def apply_async(self, *args: Any, **kwargs: Any) -> CeleryTaskResult[R]:
        return CeleryTaskResult(result=self.task.apply_async(*args, **kwargs))

    async def aapply_async(self, *args: Any, **kwargs: Any) -> CeleryTaskResult[R]:
        return await asyncio.to_thread(self.apply_async, *args, **kwargs)


@dataclass(kw_only=True)
class BaseTasksRegistry:
    _celery_app: Celery

    def _get_task_by_name[**P, R](self, name: str) -> CeleryTask[P, R]:
        try:
            task = self._celery_app.tasks[name]
        except KeyError as e:
            msg = f"Task with name '{name}' not found in registry."
            raise TaskNotFoundError(msg) from e

        return CeleryTask(task=task)
