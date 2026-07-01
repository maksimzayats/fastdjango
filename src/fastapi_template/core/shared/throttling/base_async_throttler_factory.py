from abc import ABC, abstractmethod

from throttled.asyncio import Quota, RateLimiterType, Throttled

from fastapi_template.foundation.factory import BaseFactory


class BaseAsyncThrottlerFactory(BaseFactory, ABC):
    """Factory contract for async throttled rate-limiters."""

    @abstractmethod
    def __call__(
        self,
        quota: Quota,
        using: RateLimiterType = RateLimiterType.TOKEN_BUCKET,
    ) -> Throttled:
        """Provide an async rate limiter for a quota and algorithm.

        Returns:
            A configured async throttler.
        """
        raise NotImplementedError

    @abstractmethod
    async def dispose(self) -> None:
        """Release shared throttling resources owned by the factory."""
        raise NotImplementedError
