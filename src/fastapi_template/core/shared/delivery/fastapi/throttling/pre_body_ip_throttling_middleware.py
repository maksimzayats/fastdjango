from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from fastapi_template.core.shared.delivery.fastapi.throttling.pre_body_ip_throttling_rule import (
    PreBodyIPThrottlingRule,
)

type PreBodyIPThrottlingKey = tuple[str, str]


class PreBodyIPThrottlingMiddleware:
    """Apply selected IP throttles before route body parsing."""

    __slots__ = ("_app", "_rules_by_key")

    def __init__(
        self,
        app: ASGIApp,
        *,
        rules: tuple[PreBodyIPThrottlingRule, ...],
    ) -> None:
        """Index route-specific throttling rules before ASGI request handling."""
        self._app = app
        self._rules_by_key = {(rule.method.upper(), rule.path): rule for rule in rules}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Apply a matching pre-body throttle before routing."""
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request = Request(scope=scope, receive=receive)
        rule = self._rules_by_key.get(_request_key(request=request))
        if rule is None:
            await self._app(scope, receive, send)
            return

        try:
            await rule.throttler(request)
        except HTTPException as exception:
            response = JSONResponse(
                content={"detail": exception.detail},
                status_code=exception.status_code,
                headers=exception.headers,
            )
            await response(scope, receive, send)
            return

        await self._app(scope, receive, send)


def _request_key(*, request: Request) -> PreBodyIPThrottlingKey:
    return (request.method.upper(), request.url.path)
