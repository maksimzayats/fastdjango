import pytest

from modern_python_template.core.health.delivery.celery.schemas import PingResultSchema
from tests.integration.factories import TestCeleryWorkerFactory, TestTasksRegistryFactory


class TestPingTaskController:
    """Tests for PingTaskController."""

    @pytest.mark.anyio
    async def test_ping_task(
        self,
        celery_worker_factory: TestCeleryWorkerFactory,
        tasks_registry_factory: TestTasksRegistryFactory,
    ) -> None:
        registry = tasks_registry_factory()
        with celery_worker_factory():
            result = await registry.ping.adelay()
            ping_result = await result.aget(timeout=10)

        assert ping_result == PingResultSchema(result="pong")
