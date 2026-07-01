from dataclasses import dataclass

from diwire import Injected
from throttled import RedisStore

from fastapi_template.foundation.factory import BaseFactory
from fastapi_template.infrastructure.throttled.settings import ThrottledRedisSettings


@dataclass(kw_only=True)
class ThrottlerStoreFactory(BaseFactory):
    """Factory for synchronous Redis stores used by throttled utilities."""

    _redis_settings: Injected[ThrottledRedisSettings]

    def __call__(self) -> RedisStore:
        """Build a synchronous Redis throttling store.

        Returns:
        A Redis-backed throttling store.
        """
        return RedisStore(server=self._redis_settings.url.get_secret_value())
