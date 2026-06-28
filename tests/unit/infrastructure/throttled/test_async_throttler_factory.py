from typing import Any, cast

import pytest
from throttled.asyncio import Quota as AsyncQuota

from fastapi_template.infrastructure.throttled import (
    async_throttler_factory as async_throttler_factory_module,
)
from fastapi_template.infrastructure.throttled.async_store_factory import AsyncThrottlerStoreFactory
from fastapi_template.infrastructure.throttled.async_throttler_factory import AsyncThrottlerFactory


class FakeStore:
    pass


class FakeThrottled:
    def __init__(self, *, using: str, quota: object, store: object) -> None:
        self.using = using
        self.quota = quota
        self.store = store


class FakeStoreFactory:
    def __init__(self, *, store: FakeStore) -> None:
        self.store = store

    def __call__(self) -> FakeStore:
        return self.store


def test_async_throttler_factory_builds_token_bucket_throttler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(async_throttler_factory_module, "AsyncThrottled", FakeThrottled)
    store = FakeStore()

    result = AsyncThrottlerFactory(
        _store_factory=cast(
            AsyncThrottlerStoreFactory,
            FakeStoreFactory(store=store),
        ),
    )(cast(AsyncQuota, object()))
    fake_result = cast(Any, result)

    assert fake_result.store is store
    assert fake_result.using == "token_bucket"
