from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from diwire import Injected
from starlette.requests import Request
from throttled.asyncio import Quota, RateLimiterType

from fastapi_template.core.authentication.delivery.fastapi.throttling.user_throttler import (
    UserThrottler,
)
from fastapi_template.core.shared.throttling.base_async_throttler_factory import (
    BaseAsyncThrottlerFactory,
)
from fastapi_template.foundation.factory import BaseFactory


@dataclass(kw_only=True)
class UserThrottlerFactory(BaseFactory):
    """Factory for FastAPI dependencies that throttle per authenticated user."""

    _throttler_factory: Injected[BaseAsyncThrottlerFactory]

    def __call__(
        self,
        quota: Quota,
        using: RateLimiterType = RateLimiterType.TOKEN_BUCKET,
        cost: int = 1,
    ) -> Callable[[Request], Awaitable[None]]:
        """Create a user-keyed throttling dependency for a route quota.

        Returns:
            A FastAPI dependency callable that enforces the configured quota.
        """
        throttler = self._throttler_factory(
            quota=quota,
            using=using,
        )

        return UserThrottler(
            _throttler=throttler,
            _cost=cost,
        ).__call__

    async def dispose(self) -> None:
        """Release shared throttling resources owned by the inner factory."""
        await self._throttler_factory.dispose()
