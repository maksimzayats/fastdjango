from typing import cast

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.types import Scope
from throttled.asyncio import Throttled

from fastapi_template.core.shared.delivery.fastapi.request import (
    RequestInfoService,
    RequestInfoServiceSettings,
)
from fastapi_template.core.shared.delivery.fastapi.throttling.ip_throttler import IPThrottler


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


class ThrottleResult:
    limited = False


class LimitedThrottleResult:
    limited = True


class CapturingThrottled:
    def __init__(self, *, limited: bool = False) -> None:
        self._limited = limited

    key: str | None = None
    cost: int | None = None

    async def limit(self, *, key: str, cost: int) -> ThrottleResult | LimitedThrottleResult:
        self.key = key
        self.cost = cost
        if self._limited:
            return LimitedThrottleResult()

        return ThrottleResult()


def build_request(
    *,
    headers: dict[str, str] | None = None,
    client: tuple[str, int] | None = ("192.0.2.10", 12345),
) -> Request:
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/auth/token",
        "raw_path": b"/api/v1/auth/token",
        "query_string": b"",
        "headers": [
            (name.lower().encode(), value.encode()) for name, value in (headers or {}).items()
        ],
        "client": client,
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_request_info_uses_remote_ip_when_forwarded_header_is_untrusted() -> None:
    service = RequestInfoService(_settings=RequestInfoServiceSettings())
    request = build_request(
        headers={"x-forwarded-for": "203.0.113.10, 198.51.100.5"},
        client=("192.0.2.10", 12345),
    )

    assert service.get_user_ip_trace(request=request) == "192.0.2.10"


def test_request_info_uses_configured_ip_header_when_trusted() -> None:
    service = RequestInfoService(
        _settings=RequestInfoServiceSettings(trust_forwarded_ip_header=True),
    )
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


def test_request_info_uses_remote_ip_when_trusted_header_is_missing() -> None:
    service = RequestInfoService(
        _settings=RequestInfoServiceSettings(trust_forwarded_ip_header=True),
    )
    request = build_request(client=("192.0.2.10", 12345))

    assert service.get_user_ip_trace(request=request) == "192.0.2.10"


def test_request_info_falls_back_to_remote_ip_when_forwarded_trace_is_invalid() -> None:
    service = RequestInfoService(
        _settings=RequestInfoServiceSettings(trust_forwarded_ip_header=True),
    )
    request = build_request(
        headers={"x-forwarded-for": "not-an-ip, 198.51.100.5"},
        client=("192.0.2.10", 12345),
    )

    assert service.get_user_ip_trace(request=request) == "192.0.2.10"


def test_request_info_falls_back_to_remote_ip_when_forwarded_trace_is_empty() -> None:
    service = RequestInfoService(
        _settings=RequestInfoServiceSettings(trust_forwarded_ip_header=True),
    )
    request = build_request(
        headers={"x-forwarded-for": "203.0.113.10, "},
        client=("192.0.2.10", 12345),
    )

    assert service.get_user_ip_trace(request=request) == "192.0.2.10"


def test_request_info_returns_none_when_no_valid_address_exists() -> None:
    service = RequestInfoService(_settings=RequestInfoServiceSettings())
    request = build_request(client=("not-an-ip", 12345))

    assert service.get_user_ip_trace(request=request) is None


def test_request_info_returns_none_when_request_has_no_client() -> None:
    service = RequestInfoService(_settings=RequestInfoServiceSettings())
    request = build_request(client=None)

    assert service.get_user_ip_trace(request=request) is None


@pytest.mark.anyio
async def test_ip_throttler_uses_full_request_ip_identity() -> None:
    service = RequestInfoService(
        _settings=RequestInfoServiceSettings(trust_forwarded_ip_header=True),
    )
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

    assert captured_throttler.key == ("throttler:get:/api/v1/auth/token:203.0.113.10,198.51.100.5")
    assert captured_throttler.cost == 1


@pytest.mark.anyio
async def test_ip_throttler_rejects_limited_request() -> None:
    service = RequestInfoService(_settings=RequestInfoServiceSettings())
    request = build_request(client=("192.0.2.10", 12345))
    throttler = IPThrottler(
        _throttler=cast(Throttled, CapturingThrottled(limited=True)),
        _request_info_service=service,
    )

    with pytest.raises(HTTPException) as exc_info:
        await throttler(request=request)

    assert exc_info.value.status_code == 429
