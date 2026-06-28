from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

from diwire import Injected
from starlette.requests import Request
from throttled.asyncio import Quota, RateLimiterType

from fastapi_template.core.authentication.delivery.fastapi.auth import AuthenticatedRequest
from fastapi_template.core.shared.delivery.fastapi.throttling import BaseThrottler
from fastapi_template.foundation.factories import BaseFactory
from fastapi_template.infrastructure.throttled.throttler import AsyncThrottlerFactory


@dataclass(kw_only=True)
class UserThrottlerFactory(BaseFactory):
    _throttler_factory: Injected[AsyncThrottlerFactory]

    def __call__(
        self,
        quota: Quota,
        using: RateLimiterType = RateLimiterType.TOKEN_BUCKET,
        cost: int = 1,
    ) -> Callable[[Request], Awaitable[None]]:
        throttler = self._throttler_factory(
            quota=quota,
            using=using,
        )

        return UserThrottler(
            _throttler=throttler,
            _cost=cost,
        ).__call__


@dataclass(kw_only=True)
class UserThrottler(BaseThrottler):
    def _build_key(self, request: Any) -> str:
        request = cast(AuthenticatedRequest, request)
        user_id = request.state.user.id
        path = request.url.path
        method = request.method

        return f"throttler:{method}:{path}:{user_id}".lower()
