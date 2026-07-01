import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, cast

from diwire import Injected
from throttled.asyncio import (
    Quota as AsyncQuota,
    RateLimiterType as AsyncRateLimiterType,
    RedisStore as AsyncRedisStore,
    Throttled as AsyncThrottled,
)

from fastapi_template.core.shared.throttling.base_async_throttler_factory import (
    BaseAsyncThrottlerFactory,
)
from fastapi_template.infrastructure.throttled.async_store_factory import (
    AsyncThrottlerStoreFactory,
)

type _CloseMethod = Callable[[], Awaitable[None] | None]


@dataclass(kw_only=True)
class AsyncThrottlerFactory(BaseAsyncThrottlerFactory):
    """Create async throttled rate-limiters backed by Redis."""

    _store_factory: Injected[AsyncThrottlerStoreFactory]

    _store: AsyncRedisStore | None = field(init=False)

    def __post_init__(self) -> None:
        """Create the shared async Redis store once per factory instance."""
        self._store = self._store_factory()

    def __call__(
        self,
        quota: AsyncQuota,
        using: AsyncRateLimiterType = AsyncRateLimiterType.TOKEN_BUCKET,
    ) -> AsyncThrottled:
        """Provide an async Redis-backed rate limiter for a quota.

        Returns:
            A configured async throttler.
        """
        store = self._get_store()
        return AsyncThrottled(
            using=using.value,
            quota=quota,
            store=cast(Any, store),
        )

    async def dispose(self) -> None:
        """Close the Redis client held by the throttling store, if one was opened."""
        store = self._store
        self._store = None
        if store is None:
            return

        client = _existing_redis_client(store=store)
        if client is None:
            return

        close_method = _close_method(client=client)
        if close_method is None:
            return

        close_result = close_method()
        if inspect.isawaitable(close_result):
            await close_result

    def _get_store(self) -> AsyncRedisStore:
        store = self._store
        if store is None:
            store = self._store_factory()
            self._store = store

        return store


def _existing_redis_client(*, store: AsyncRedisStore) -> object | None:
    backend = object.__getattribute__(store, "_backend")
    return cast(object | None, object.__getattribute__(backend, "_client"))


def _close_method(*, client: object) -> _CloseMethod | None:
    for method_name in ("aclose", "close", "disconnect"):
        method = getattr(client, method_name, None)
        if callable(method):
            return cast(_CloseMethod, method)

    return None
