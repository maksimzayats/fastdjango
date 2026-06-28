from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from diwire import Injected
from starlette.requests import Request
from throttled.asyncio import Quota, RateLimiterType

from fastapi_template.core.authentication.delivery.fastapi.throttling.user_throttler import (
    UserThrottler,
)
from fastapi_template.foundation.factory import BaseFactory
from fastapi_template.infrastructure.throttled.async_throttler_factory import (
    AsyncThrottlerFactory,
)


@dataclass(kw_only=True)
class UserThrottlerFactory(BaseFactory):
    """Define UserThrottlerFactory."""

    _throttler_factory: Injected[AsyncThrottlerFactory]

    def __call__(
        self,
        quota: Quota,
        using: RateLimiterType = RateLimiterType.TOKEN_BUCKET,
        cost: int = 1,
    ) -> Callable[[Request], Awaitable[None]]:
        """Run call.

        Returns:
        The operation result.
        """
        throttler = self._throttler_factory(
            quota=quota,
            using=using,
        )

        return UserThrottler(
            _throttler=throttler,
            _cost=cost,
        ).__call__
