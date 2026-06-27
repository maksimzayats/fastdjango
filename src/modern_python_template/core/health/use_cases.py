import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from diwire import Injected
from django.contrib.sessions.models import Session

from modern_python_template.core.health.exceptions import HealthCheckError
from modern_python_template.entrypoints.celery.registry import TasksRegistry
from modern_python_template.foundation.use_cases import BaseUseCase

if TYPE_CHECKING:
    from modern_python_template.core.health.delivery.celery.schemas import PingResultSchema
    from modern_python_template.infrastructure.celery.registry import CeleryTaskResult

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class SystemHealthUseCase(BaseUseCase):
    HEALTH_CHECK_ERROR: ClassVar = HealthCheckError
    UNEXPECTED_ERROR: ClassVar = Exception

    CELERY_PING_TIMEOUT_SECONDS: ClassVar = 5
    CELERY_RESULT_FORGET_TIMEOUT_SECONDS: ClassVar = 1

    _tasks_registry: Injected[TasksRegistry]

    async def check(self) -> None:
        """Check the health of the system components."""
        await self._check_database()
        await self._check_celery_ping()

    async def _check_database(self) -> None:
        try:
            # Perform a simple database query to check connectivity
            await Session.objects.afirst()
        except self.UNEXPECTED_ERROR as e:
            logger.exception("Health check failed: database is not reachable")
            raise self.HEALTH_CHECK_ERROR from e

    async def _check_celery_ping(self) -> None:
        ping_result = await self._get_celery_ping_result()

        if ping_result.get("result") != "pong":
            logger.error("Health check failed: Celery ping task returned %r", ping_result)
            raise self.HEALTH_CHECK_ERROR

    async def _get_celery_ping_result(self) -> PingResultSchema:
        task_result: CeleryTaskResult[PingResultSchema] | None = None

        try:
            async with asyncio.timeout(self.CELERY_PING_TIMEOUT_SECONDS):
                task_result = await self._tasks_registry.ping.adelay()
                return await self._read_celery_ping_result(task_result=task_result)
        except self.UNEXPECTED_ERROR as e:
            logger.exception("Health check failed: Celery ping task did not complete")
            raise self.HEALTH_CHECK_ERROR from e
        finally:
            if task_result is not None:
                await self._forget_celery_ping_result(task_result=task_result)

    async def _read_celery_ping_result(
        self,
        *,
        task_result: CeleryTaskResult[PingResultSchema],
    ) -> PingResultSchema:
        return await task_result.aget(timeout=self.CELERY_PING_TIMEOUT_SECONDS)

    async def _forget_celery_ping_result(
        self,
        *,
        task_result: CeleryTaskResult[PingResultSchema],
    ) -> None:
        try:
            await task_result.aforget(timeout=self.CELERY_RESULT_FORGET_TIMEOUT_SECONDS)
        except self.UNEXPECTED_ERROR:
            logger.warning(
                "Failed to forget Celery health check result",
                exc_info=True,
            )
