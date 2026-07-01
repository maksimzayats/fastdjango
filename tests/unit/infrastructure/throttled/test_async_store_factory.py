from typing import cast

import pytest
from pydantic import SecretStr

from fastapi_template.infrastructure.throttled import (
    async_store_factory as async_store_factory_module,
)
from fastapi_template.infrastructure.throttled.async_store_factory import AsyncThrottlerStoreFactory
from fastapi_template.infrastructure.throttled.settings import ThrottledRedisSettings


class FakeStore:
    def __init__(self, *, server: str) -> None:
        self.server = server


def test_async_store_factory_builds_redis_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(async_store_factory_module, "AsyncRedisStore", FakeStore)

    store = AsyncThrottlerStoreFactory(_redis_settings=_redis_settings())()
    fake_store = cast(FakeStore, store)

    assert fake_store.server == "redis://localhost:6379/0"


def _redis_settings() -> ThrottledRedisSettings:
    return ThrottledRedisSettings(url=SecretStr("redis://localhost:6379/0"))
