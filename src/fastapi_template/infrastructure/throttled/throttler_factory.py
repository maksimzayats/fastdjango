from dataclasses import dataclass, field
from typing import Any, cast

from diwire import Injected
from throttled import Quota, RateLimiterType, RedisStore, Throttled

from fastapi_template.foundation.factory import BaseFactory
from fastapi_template.infrastructure.throttled.store_factory import ThrottlerStoreFactory


@dataclass(kw_only=True)
class ThrottlerFactory(BaseFactory):
    """Create synchronous throttled rate-limiters backed by Redis."""

    _store_factory: Injected[ThrottlerStoreFactory]

    _store: RedisStore = field(init=False)

    def __post_init__(self) -> None:
        """Create the shared Redis store once per factory instance."""
        self._store = self._store_factory()

    def __call__(
        self,
        quota: Quota,
        using: RateLimiterType = RateLimiterType.TOKEN_BUCKET,
    ) -> Throttled:
        """Provide a synchronous Redis-backed rate limiter for a quota.

        Returns:
            A configured throttler.
        """
        return Throttled(
            using=using.value,
            quota=quota,
            store=cast(Any, self._store),
        )
