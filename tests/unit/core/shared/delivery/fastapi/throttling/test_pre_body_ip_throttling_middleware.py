from collections.abc import Awaitable, Callable
from http import HTTPStatus

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.requests import Request
from starlette.types import Message, Scope

from fastapi_template.core.shared.delivery.fastapi.throttling.pre_body_ip_throttling_middleware import (
    PreBodyIPThrottlingMiddleware,
)
from fastapi_template.core.shared.delivery.fastapi.throttling.pre_body_ip_throttling_rule import (
    PreBodyIPThrottlingRule,
)

_THROTTLED_PATH = "/api/v1/users"


class BodyPayload(BaseModel):
    value: str


class RecordingEndpoint:
    called = False

    async def __call__(self, body: BodyPayload) -> dict[str, str]:
        self.called = True
        return {"value": body.value}


class RecordingThrottler:
    def __init__(self, *, limited: bool = False) -> None:
        self._limited = limited
        self.called_paths: list[str] = []

    async def __call__(self, request: Request) -> None:
        self.called_paths.append(request.url.path)
        if self._limited:
            raise HTTPException(
                status_code=HTTPStatus.TOO_MANY_REQUESTS,
                detail="Too many requests",
            )


class RecordingASGIApp:
    called = False

    async def __call__(
        self,
        scope: Scope,
        receive: Callable[[], Awaitable[Message]],
        send: Callable[[Message], Awaitable[None]],
    ) -> None:
        self.called = True


def test_pre_body_ip_throttling_rejects_before_body_parsing() -> None:
    endpoint = RecordingEndpoint()
    throttler = RecordingThrottler(limited=True)
    app = _build_app(path=_THROTTLED_PATH, endpoint=endpoint, throttler=throttler)

    with TestClient(app) as test_client:
        response = test_client.post(
            _THROTTLED_PATH,
            content="{",
            headers={"content-type": "application/json"},
        )

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert throttler.called_paths == [_THROTTLED_PATH]
    assert endpoint.called is False


def test_pre_body_ip_throttling_allows_matching_requests() -> None:
    endpoint = RecordingEndpoint()
    throttler = RecordingThrottler()
    app = _build_app(path=_THROTTLED_PATH, endpoint=endpoint, throttler=throttler)

    with TestClient(app) as test_client:
        response = test_client.post(_THROTTLED_PATH, json={"value": "ok"})

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"value": "ok"}
    assert throttler.called_paths == [_THROTTLED_PATH]
    assert endpoint.called is True


def test_pre_body_ip_throttling_ignores_unmatched_routes() -> None:
    endpoint = RecordingEndpoint()
    throttler = RecordingThrottler(limited=True)
    app = _build_app(path="/api/v1/other", endpoint=endpoint, throttler=throttler)

    with TestClient(app) as test_client:
        response = test_client.post(_THROTTLED_PATH, json={"value": "ok"})

    assert response.status_code == HTTPStatus.OK
    assert throttler.called_paths == []
    assert endpoint.called is True


@pytest.mark.anyio
async def test_pre_body_ip_throttling_ignores_non_http_scopes() -> None:
    app = RecordingASGIApp()
    middleware = PreBodyIPThrottlingMiddleware(app, rules=())

    await middleware(
        {"type": "websocket"},
        _empty_receive,
        _empty_send,
    )

    assert app.called is True


def _build_app(
    *,
    path: str,
    endpoint: RecordingEndpoint,
    throttler: RecordingThrottler,
) -> FastAPI:
    app = FastAPI()
    app.add_api_route(_THROTTLED_PATH, endpoint, methods=["POST"])
    app.add_middleware(
        PreBodyIPThrottlingMiddleware,
        rules=(
            PreBodyIPThrottlingRule(
                method="POST",
                path=path,
                throttler=throttler,
            ),
        ),
    )
    return app


async def _empty_receive() -> Message:
    return {"type": "http.disconnect"}


async def _empty_send(message: Message) -> None:
    return None
