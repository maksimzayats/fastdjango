from dataclasses import dataclass

from diwire import Injected
from starlette.requests import Request

from fastapi_template.core.shared.delivery.fastapi.request import RequestInfoService
from fastapi_template.core.shared.delivery.fastapi.throttling.base import BaseThrottler


@dataclass(kw_only=True)
class IPThrottler(BaseThrottler):
    """Rate limiter keyed by request method, path, and client IP trace."""

    _request_info_service: Injected[RequestInfoService]

    def _build_key(self, request: Request) -> str:
        user_ip = self._request_info_service.get_user_ip_trace(request=request)
        path = request.url.path
        method = request.method

        return f"throttler:{method}:{path}:{user_ip}".lower()
