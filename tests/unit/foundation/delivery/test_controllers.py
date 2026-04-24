from typing import Any

import pytest

from fastdjango.foundation.delivery.controllers import BaseAsyncController, BaseController


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


class HandledError(Exception):
    pass


class SyncController(BaseController):
    def register(self, registry: Any) -> None:
        pass

    def route(self) -> str:
        raise HandledError

    def handle_exception(self, exception: Exception) -> str:
        return type(exception).__name__


class AsyncRouteOnSyncController(BaseController):
    def register(self, registry: Any) -> None:
        pass

    async def route(self) -> str:
        raise HandledError

    def handle_exception(self, exception: Exception) -> str:
        return type(exception).__name__


class AsyncController(BaseAsyncController):
    def register(self, registry: Any) -> None:
        pass

    async def route(self) -> str:
        raise HandledError

    async def handle_exception(self, exception: Exception) -> str:
        return type(exception).__name__


class SyncRouteOnAsyncController(BaseAsyncController):
    def register(self, registry: Any) -> None:
        pass

    def route(self) -> str:
        raise HandledError

    async def handle_exception(self, exception: Exception) -> str:
        return type(exception).__name__


def test_controller_handles_sync_route_exceptions() -> None:
    controller = SyncController()

    result = controller.route()

    assert result == "HandledError"


def test_sync_controller_rejects_async_routes() -> None:
    with pytest.raises(TypeError, match="BaseAsyncController"):
        AsyncRouteOnSyncController()


@pytest.mark.anyio
async def test_async_controller_handles_async_route_exceptions() -> None:
    controller = AsyncController()

    result = await controller.route()

    assert result == "HandledError"


def test_async_controller_rejects_sync_routes() -> None:
    with pytest.raises(TypeError, match="BaseController"):
        SyncRouteOnAsyncController()
