import logging
from dataclasses import dataclass

from fastapi import HTTPException
from starlette import status
from starlette.requests import Request
from throttled.asyncio import Quota, RateLimiterType, Throttled

from delivery.http.services.request import RequestInfoService
from infrastructure.throttler.throttler import AsyncThrottlerFactory

logger = logging.getLogger(__name__)


@dataclass
class IPThrottlerFactory:
    _throttler_factory: AsyncThrottlerFactory
    _request_info_service: RequestInfoService

    def __call__(
        self,
        quota: Quota,
        using: RateLimiterType = RateLimiterType.TOKEN_BUCKET,
        cost: int = 1,
    ) -> IPThrottler:
        throttler = self._throttler_factory(
            quota=quota,
            using=using,
        )

        return IPThrottler(
            throttler=throttler,
            request_info_service=self._request_info_service,
            cost=cost,
        )


class IPThrottler:
    def __init__(
        self,
        throttler: Throttled,
        request_info_service: RequestInfoService,
        cost: int = 1,
    ) -> None:
        self._throttler = throttler
        self._request_info_service = request_info_service
        self._cost = cost

    async def __call__(self, request: Request) -> None:
        key = self._build_key(request=request)

        logger.debug("Throttling key: %s", key)
        result = await self._throttler.limit(key=key, cost=self._cost)
        logger.debug("Throttling result: limited=%s", result.limited)

        if result.limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
            )

    def _build_key(self, request: Request) -> str:
        user_ip = self._request_info_service.get_user_ip(request=request)
        path = request.url.path
        method = request.method

        return f"throttler:{method}:{path}:{user_ip}".lower()
