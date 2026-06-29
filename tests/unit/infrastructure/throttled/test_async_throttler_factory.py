from typing import Any, cast

import pytest
from throttled.asyncio import Quota as AsyncQuota

from fastapi_template.infrastructure.throttled import (
    async_throttler_factory as async_throttler_factory_module,
)
from fastapi_template.infrastructure.throttled.async_store_factory import AsyncThrottlerStoreFactory
from fastapi_template.infrastructure.throttled.async_throttler_factory import AsyncThrottlerFactory


class FakeStore:
    def __init__(self, *, client: object | None = None) -> None:
        self._backend = FakeStoreBackend(client=client)


class FakeStoreBackend:
    def __init__(self, *, client: object | None) -> None:
        self._client = client


class FakeRedisClient:
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


class FakeSyncCloseClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


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


class SequencedStoreFactory:
    def __init__(self, *, stores: list[FakeStore]) -> None:
        self._stores = stores

    def __call__(self) -> FakeStore:
        return self._stores.pop(0)


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


@pytest.mark.anyio
async def test_async_throttler_factory_disposes_existing_redis_client() -> None:
    client = FakeRedisClient()

    factory = AsyncThrottlerFactory(
        _store_factory=cast(
            AsyncThrottlerStoreFactory,
            FakeStoreFactory(store=FakeStore(client=client)),
        ),
    )

    await factory.dispose()

    assert client.closed is True


@pytest.mark.anyio
async def test_async_throttler_factory_ignores_store_without_open_client() -> None:
    factory = AsyncThrottlerFactory(
        _store_factory=cast(
            AsyncThrottlerStoreFactory,
            FakeStoreFactory(store=FakeStore(client=None)),
        ),
    )

    await factory.dispose()
    await factory.dispose()


@pytest.mark.anyio
async def test_async_throttler_factory_supports_sync_close_clients() -> None:
    client = FakeSyncCloseClient()
    factory = AsyncThrottlerFactory(
        _store_factory=cast(
            AsyncThrottlerStoreFactory,
            FakeStoreFactory(store=FakeStore(client=client)),
        ),
    )

    await factory.dispose()

    assert client.closed is True


@pytest.mark.anyio
async def test_async_throttler_factory_recreates_store_after_dispose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(async_throttler_factory_module, "AsyncThrottled", FakeThrottled)
    recreated_store = FakeStore(client=None)
    factory = AsyncThrottlerFactory(
        _store_factory=cast(
            AsyncThrottlerStoreFactory,
            SequencedStoreFactory(
                stores=[
                    FakeStore(client=None),
                    recreated_store,
                ],
            ),
        ),
    )

    await factory.dispose()
    result = factory(cast(AsyncQuota, object()))

    assert cast(Any, result).store is recreated_store
