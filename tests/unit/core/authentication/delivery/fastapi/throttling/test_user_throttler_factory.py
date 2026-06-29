from typing import cast

import pytest
from throttled.asyncio import Quota, RateLimiterType, Throttled

from fastapi_template.core.authentication.delivery.fastapi.throttling.user_throttler_factory import (
    UserThrottlerFactory,
)
from fastapi_template.core.shared.throttling.base_async_throttler_factory import (
    BaseAsyncThrottlerFactory,
)


class DisposableThrottlerFactory:
    def __init__(self) -> None:
        self.disposed = False

    def __call__(
        self,
        quota: Quota,
        using: RateLimiterType = RateLimiterType.TOKEN_BUCKET,
    ) -> Throttled:
        return cast(Throttled, object())

    async def dispose(self) -> None:
        self.disposed = True


@pytest.mark.anyio
async def test_user_throttler_factory_delegates_disposal() -> None:
    throttler_factory = DisposableThrottlerFactory()
    factory = UserThrottlerFactory(
        _throttler_factory=cast(BaseAsyncThrottlerFactory, throttler_factory),
    )

    await factory.dispose()

    assert throttler_factory.disposed is True
