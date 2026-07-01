from dataclasses import dataclass
from typing import Any, cast

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request import (
    AuthenticatedRequest,
)
from fastapi_template.core.shared.delivery.fastapi.throttling.base import BaseThrottler


@dataclass(kw_only=True)
class UserThrottler(BaseThrottler):
    """Rate limiter keyed by an authenticated user identifier."""

    def _build_key(self, request: Any) -> str:
        request = cast(AuthenticatedRequest, request)
        user_id = request.state.user_id
        path = request.url.path
        method = request.method

        return f"throttler:{method}:{path}:{user_id}".lower()
