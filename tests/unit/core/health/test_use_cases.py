import asyncio
from typing import cast

import pytest

from modern_python_template.core.health import use_cases as health_use_cases
from modern_python_template.core.health.use_cases import SystemHealthUseCase
from modern_python_template.entrypoints.celery.registry import TasksRegistry


class WorkingSessionManager:
    async def afirst(self) -> None:
        return None


class WorkingSession:
    objects = WorkingSessionManager()


class BrokenSessionManager:
    async def afirst(self) -> None:
        msg = "database unavailable"
        raise RuntimeError(msg)


class BrokenSession:
    objects = BrokenSessionManager()


class FakeTaskResult:
    def __init__(
        self,
        *,
        payload: object | None = None,
        error: Exception | None = None,
        delay_seconds: float = 0,
    ) -> None:
        self._payload = {"result": "pong"} if payload is None else payload
        self._error = error
        self._delay_seconds = delay_seconds
        self.get_timeout: float | None = None
        self.forget_timeout: float | None = None
        self.forgot = False

    async def aget(self, *, timeout: float | None = None) -> object:  # noqa: ASYNC109
        self.get_timeout = timeout

        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)

        if self._error is not None:
            raise self._error

        return self._payload

    async def aforget(self, *, timeout: float | None = None) -> None:  # noqa: ASYNC109
        self.forget_timeout = timeout
        self.forgot = True


class FakePingTask:
    def __init__(
        self,
        task_result: FakeTaskResult,
        *,
        error: Exception | None = None,
        delay_seconds: float = 0,
    ) -> None:
        self._task_result = task_result
        self._error = error
        self._delay_seconds = delay_seconds
        self.called = False

    async def adelay(self) -> FakeTaskResult:
        self.called = True

        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)

        if self._error is not None:
            raise self._error

        return self._task_result


class FakeTasksRegistry:
    def __init__(self, ping_task: FakePingTask) -> None:
        self.ping = ping_task


@pytest.mark.anyio
async def test_health_check_checks_database_and_celery_ping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_use_cases, "Session", WorkingSession)
    ping_task, task_result, registry = _build_registry()
    use_case = SystemHealthUseCase(_tasks_registry=registry)

    await use_case.check()

    assert ping_task.called is True
    assert task_result.get_timeout == SystemHealthUseCase.CELERY_PING_TIMEOUT_SECONDS
    assert task_result.forget_timeout == (SystemHealthUseCase.CELERY_RESULT_FORGET_TIMEOUT_SECONDS)
    assert task_result.forgot is True


@pytest.mark.anyio
async def test_health_check_maps_database_errors_to_health_check_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_use_cases, "Session", BrokenSession)
    ping_task, _, registry = _build_registry()
    use_case = SystemHealthUseCase(_tasks_registry=registry)

    with pytest.raises(SystemHealthUseCase.HEALTH_CHECK_ERROR):
        await use_case.check()

    assert ping_task.called is False


@pytest.mark.anyio
async def test_health_check_maps_celery_result_errors_to_health_check_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_use_cases, "Session", WorkingSession)
    _, task_result, registry = _build_registry(error=TimeoutError)
    use_case = SystemHealthUseCase(_tasks_registry=registry)

    with pytest.raises(SystemHealthUseCase.HEALTH_CHECK_ERROR):
        await use_case.check()

    assert task_result.forgot is True


@pytest.mark.anyio
async def test_health_check_maps_celery_enqueue_errors_to_health_check_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_use_cases, "Session", WorkingSession)
    ping_task, task_result, registry = _build_registry(enqueue_error=ConnectionError)
    use_case = SystemHealthUseCase(_tasks_registry=registry)

    with pytest.raises(SystemHealthUseCase.HEALTH_CHECK_ERROR):
        await use_case.check()

    assert ping_task.called is True
    assert task_result.forgot is False


@pytest.mark.anyio
async def test_health_check_maps_celery_enqueue_timeout_to_health_check_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_use_cases, "Session", WorkingSession)
    monkeypatch.setattr(SystemHealthUseCase, "CELERY_PING_TIMEOUT_SECONDS", 0.01)
    ping_task, task_result, registry = _build_registry(enqueue_delay_seconds=1)
    use_case = SystemHealthUseCase(_tasks_registry=registry)

    with pytest.raises(SystemHealthUseCase.HEALTH_CHECK_ERROR):
        await use_case.check()

    assert ping_task.called is True
    assert task_result.forgot is False


@pytest.mark.anyio
async def test_health_check_forgets_celery_result_after_read_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_use_cases, "Session", WorkingSession)
    monkeypatch.setattr(SystemHealthUseCase, "CELERY_PING_TIMEOUT_SECONDS", 0.01)
    _, task_result, registry = _build_registry(result_delay_seconds=1)
    use_case = SystemHealthUseCase(_tasks_registry=registry)

    with pytest.raises(SystemHealthUseCase.HEALTH_CHECK_ERROR):
        await use_case.check()

    assert task_result.forgot is True


@pytest.mark.anyio
async def test_health_check_maps_unexpected_celery_payload_to_health_check_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health_use_cases, "Session", WorkingSession)
    _, task_result, registry = _build_registry(payload={"result": "nope"})
    use_case = SystemHealthUseCase(_tasks_registry=registry)

    with pytest.raises(SystemHealthUseCase.HEALTH_CHECK_ERROR):
        await use_case.check()

    assert task_result.forgot is True


def _build_registry(
    *,
    payload: object | None = None,
    error: type[Exception] | None = None,
    enqueue_error: type[Exception] | None = None,
    enqueue_delay_seconds: float = 0,
    result_delay_seconds: float = 0,
) -> tuple[FakePingTask, FakeTaskResult, TasksRegistry]:
    task_result = FakeTaskResult(
        payload=payload,
        error=error() if error is not None else None,
        delay_seconds=result_delay_seconds,
    )
    ping_task = FakePingTask(
        task_result=task_result,
        error=enqueue_error() if enqueue_error is not None else None,
        delay_seconds=enqueue_delay_seconds,
    )
    registry = FakeTasksRegistry(ping_task=ping_task)

    return ping_task, task_result, cast(TasksRegistry, registry)
