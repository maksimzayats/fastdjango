from dataclasses import dataclass

from diwire import Injected
from throttled.asyncio import RedisStore as AsyncRedisStore

from fastapi_template.foundation.factory import BaseFactory
from fastapi_template.infrastructure.throttled.settings import ThrottledRedisSettings


@dataclass(kw_only=True)
class AsyncThrottlerStoreFactory(BaseFactory):
    """Factory for async Redis stores used by FastAPI throttling."""

    _redis_settings: Injected[ThrottledRedisSettings]

    def __call__(self) -> AsyncRedisStore:
        """Build an async Redis throttling store.

        Returns:
        An async Redis-backed throttling store.
        """
        return AsyncRedisStore(server=self._redis_settings.url.get_secret_value())
