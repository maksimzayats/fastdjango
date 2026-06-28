from dataclasses import dataclass, field
from typing import Any, cast

from diwire import Injected
from throttled.asyncio import (
    Quota as AsyncQuota,
    RateLimiterType as AsyncRateLimiterType,
    RedisStore as AsyncRedisStore,
    Throttled as AsyncThrottled,
)

from fastapi_template.foundation.factory import BaseFactory
from fastapi_template.infrastructure.throttled.async_store_factory import (
    AsyncThrottlerStoreFactory,
)


@dataclass(kw_only=True)
class AsyncThrottlerFactory(BaseFactory):
    """Define AsyncThrottlerFactory."""

    _store_factory: Injected[AsyncThrottlerStoreFactory]

    _store: AsyncRedisStore = field(init=False)

    def __post_init__(self) -> None:
        """Run post init."""
        self._store = self._store_factory()

    def __call__(
        self,
        quota: AsyncQuota,
        using: AsyncRateLimiterType = AsyncRateLimiterType.TOKEN_BUCKET,
    ) -> AsyncThrottled:
        """Build an async throttler.

        Returns:
        A configured async throttler.
        """
        return AsyncThrottled(
            using=using.value,
            quota=quota,
            store=cast(Any, self._store),
        )
