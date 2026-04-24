from typing import cast

import pytest
from starlette.requests import Request
from starlette.types import Scope
from throttled.asyncio import Throttled

from fastdjango.core.shared.delivery.fastapi.request import (
    RequestInfoService,
    RequestInfoServiceSettings,
)
from fastdjango.core.shared.delivery.fastapi.throttling import IPThrottler


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


class ThrottleResult:
    limited = False


class CapturingThrottled:
    key: str | None = None
    cost: int | None = None

    async def limit(self, *, key: str, cost: int) -> ThrottleResult:
        self.key = key
        self.cost = cost
        return ThrottleResult()


def build_request(
    *,
    headers: dict[str, str] | None = None,
    client: tuple[str, int] | None = ("192.0.2.10", 12345),
) -> Request:
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/auth/token",
        "raw_path": b"/v1/auth/token",
        "query_string": b"",
        "headers": [
            (name.lower().encode(), value.encode()) for name, value in (headers or {}).items()
        ],
        "client": client,
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_request_info_uses_configured_ip_header_when_present() -> None:
    service = RequestInfoService(_settings=RequestInfoServiceSettings())
    request = build_request(
        headers={"x-forwarded-for": "203.0.113.10, 198.51.100.5"},
        client=("192.0.2.10", 12345),
    )

    assert service.get_user_ip_trace(request=request) == "203.0.113.10,198.51.100.5"


def test_request_info_uses_remote_ip_when_configured_ip_header_is_missing() -> None:
    service = RequestInfoService(_settings=RequestInfoServiceSettings())
    request = build_request(
        client=("192.0.2.10", 12345),
    )

    assert service.get_user_ip_trace(request=request) == "192.0.2.10"


def test_request_info_falls_back_to_remote_ip_when_forwarded_trace_is_invalid() -> None:
    service = RequestInfoService(_settings=RequestInfoServiceSettings())
    request = build_request(
        headers={"x-forwarded-for": "not-an-ip, 198.51.100.5"},
        client=("192.0.2.10", 12345),
    )

    assert service.get_user_ip_trace(request=request) == "192.0.2.10"


def test_request_info_returns_none_when_no_valid_address_exists() -> None:
    service = RequestInfoService(_settings=RequestInfoServiceSettings())
    request = build_request(client=("not-an-ip", 12345))

    assert service.get_user_ip_trace(request=request) is None


@pytest.mark.anyio
async def test_ip_throttler_uses_full_request_ip_identity() -> None:
    service = RequestInfoService(_settings=RequestInfoServiceSettings())
    request = build_request(
        headers={"x-forwarded-for": "203.0.113.10, 198.51.100.5"},
        client=("192.0.2.10", 12345),
    )
    captured_throttler = CapturingThrottled()
    throttler = IPThrottler(
        _throttler=cast(Throttled, captured_throttler),
        _request_info_service=service,
    )

    await throttler(request=request)

    assert captured_throttler.key == ("throttler:get:/v1/auth/token:203.0.113.10,198.51.100.5")
    assert captured_throttler.cost == 1
