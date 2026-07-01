from typing import cast

import pytest
from pydantic import SecretStr

from fastapi_template.infrastructure.throttled import store_factory as store_factory_module
from fastapi_template.infrastructure.throttled.settings import ThrottledRedisSettings
from fastapi_template.infrastructure.throttled.store_factory import ThrottlerStoreFactory


class FakeStore:
    def __init__(self, *, server: str) -> None:
        self.server = server


def test_store_factory_builds_redis_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(store_factory_module, "RedisStore", FakeStore)

    store = ThrottlerStoreFactory(_redis_settings=_redis_settings())()
    fake_store = cast(FakeStore, store)

    assert fake_store.server == "redis://localhost:6379/0"


def _redis_settings() -> ThrottledRedisSettings:
    return ThrottledRedisSettings(url=SecretStr("redis://localhost:6379/0"))
