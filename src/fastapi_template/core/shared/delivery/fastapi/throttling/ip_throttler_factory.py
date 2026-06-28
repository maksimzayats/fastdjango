from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from diwire import Injected
from starlette.requests import Request
from throttled.asyncio import Quota, RateLimiterType

from fastapi_template.core.shared.delivery.fastapi.request import RequestInfoService
from fastapi_template.core.shared.delivery.fastapi.throttling.ip_throttler import IPThrottler
from fastapi_template.foundation.factory import BaseFactory
from fastapi_template.infrastructure.throttled.async_throttler_factory import (
    AsyncThrottlerFactory,
)


@dataclass(kw_only=True)
class IPThrottlerFactory(BaseFactory):
    """Define IPThrottlerFactory."""

    _throttler_factory: Injected[AsyncThrottlerFactory]
    _request_info_service: Injected[RequestInfoService]

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

        return IPThrottler(
            _throttler=throttler,
            _request_info_service=self._request_info_service,
            _cost=cost,
        ).__call__
