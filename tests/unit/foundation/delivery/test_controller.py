from dataclasses import dataclass

import pytest

from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class SyncEndpointController(BaseAsyncController):
    def register(self, registry: object) -> None:
        return None

    def endpoint(self) -> None:
        return None


def test_async_controller_rejects_sync_public_endpoint() -> None:
    with pytest.raises(TypeError, match="must be async def"):
        SyncEndpointController()
