from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from fastdjango.infrastructure.django import controllers as controllers_module
from fastdjango.infrastructure.django.controllers import BaseTransactionController


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


class SyncTransactionController(BaseTransactionController):
    def register(self, registry: Any) -> None:
        pass

    def route(self, events: list[str]) -> str:
        events.append("route")
        return "ok"


class AsyncRouteTransactionController(BaseTransactionController):
    def register(self, registry: Any) -> None:
        pass

    async def route(self, events: list[str]) -> str:
        events.append("route")
        return "ok"


def test_transaction_controller_wraps_sync_route_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    @contextmanager
    def traced_atomic(*args: Any, **kwargs: Any) -> Iterator[None]:
        events.append("enter")
        try:
            yield
        finally:
            events.append("exit")

    monkeypatch.setattr(controllers_module, "traced_atomic", traced_atomic)
    controller = SyncTransactionController()

    result = controller.route(events=events)

    assert result == "ok"
    assert events == ["enter", "route", "exit"]


def test_transaction_controller_rejects_async_routes() -> None:
    with pytest.raises(TypeError, match="cannot use BaseTransactionController"):
        AsyncRouteTransactionController()
