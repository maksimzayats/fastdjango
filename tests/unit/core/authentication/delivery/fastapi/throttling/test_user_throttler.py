from types import SimpleNamespace
from typing import cast

import pytest
from throttled.asyncio import Throttled

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request import (
    AuthenticatedRequest,
)
from fastapi_template.core.authentication.delivery.fastapi.throttling.user_throttler import (
    UserThrottler,
)


class ThrottleResult:
    limited = False


class CapturingThrottled:
    key: str | None = None
    cost: int | None = None

    async def limit(self, *, key: str, cost: int) -> ThrottleResult:
        self.key = key
        self.cost = cost
        return ThrottleResult()


@pytest.mark.anyio
async def test_user_throttler_uses_authenticated_user_id() -> None:
    captured_throttler = CapturingThrottled()
    throttler = UserThrottler(_throttler=cast(Throttled, captured_throttler))
    request = cast(
        AuthenticatedRequest,
        SimpleNamespace(
            method="POST",
            state=SimpleNamespace(user_id=42),
            url=SimpleNamespace(path="/api/v1/auth/token/revoke"),
        ),
    )

    await throttler(request=request)

    assert captured_throttler.key == "throttler:post:/api/v1/auth/token/revoke:42"
    assert captured_throttler.cost == 1
