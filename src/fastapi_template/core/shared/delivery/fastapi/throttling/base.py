import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from starlette import status
from starlette.requests import Request
from throttled.asyncio import Throttled

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class BaseThrottler(ABC):
    """Base FastAPI dependency for rejecting requests over a rate limit."""

    _throttler: Throttled
    _cost: int = 1

    async def __call__(self, request: Request) -> None:
        """Apply the configured rate limit to the key derived from the request."""
        key = self._build_key(request=request)
        limit_result = await self._throttler.limit(key=key, cost=self._cost)
        if limit_result.limited:
            logger.debug("Request with key %s was throttled", key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
            )

        logger.debug("Request with key %s was not throttled", key)

    @abstractmethod
    def _build_key(self, request: Any) -> str: ...
