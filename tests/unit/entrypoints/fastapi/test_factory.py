from collections.abc import Awaitable, Callable, Sequence
from http import HTTPStatus
from typing import Any, Protocol, cast

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request

from fastapi_template.core.authentication.delivery.fastapi.controllers.issue_token import (
    IssueTokenController,
)
from fastapi_template.core.authentication.delivery.fastapi.controllers.refresh_token import (
    RefreshTokenController,
)
from fastapi_template.core.authentication.delivery.fastapi.controllers.revoke_token import (
    RevokeTokenController,
)
from fastapi_template.core.health.delivery.fastapi.controllers.health_check import (
    HealthCheckController,
)
from fastapi_template.core.health.delivery.fastapi.controllers.health_check_websocket import (
    HealthCheckWebSocketController,
)
from fastapi_template.core.shared.delivery.fastapi.throttling.ip_throttler_factory import (
    IPThrottlerFactory,
)
from fastapi_template.core.shared.delivery.fastapi.throttling.pre_body_ip_throttling_middleware import (
    PreBodyIPThrottlingMiddleware,
)
from fastapi_template.core.user.delivery.fastapi.controllers.create_user import (
    CreateUserController,
)
from fastapi_template.core.user.delivery.fastapi.controllers.current_user import (
    CurrentUserController,
)
from fastapi_template.core.user.delivery.fastapi.controllers.staff_user_lookup import (
    StaffUserLookupController,
)
from fastapi_template.entrypoints.fastapi.factory import (
    FastAPIFactory,
)
from fastapi_template.entrypoints.fastapi.settings.cors import CORSSettings
from fastapi_template.entrypoints.fastapi.settings.fastapi import FastAPISettings
from fastapi_template.infrastructure.environment import Environment
from fastapi_template.infrastructure.logfire.instrumentor import OpenTelemetryInstrumentor
from fastapi_template.infrastructure.settings import ApplicationSettings
from fastapi_template.infrastructure.sqlalchemy.session import SQLAlchemySessionFactory

PRE_BODY_THROTTLED_POST_PATHS = (
    "/api/v1/auth/token",
    "/api/v1/auth/token/refresh",
    "/api/v1/auth/token/revoke",
    "/api/v1/users",
)


class FakeTelemetryInstrumentor:
    instrumented_app: FastAPI | None = None

    def instrument_fastapi(self, *, app: FastAPI) -> None:
        self.instrumented_app = app


class FakeSessionFactory:
    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


class FakeController:
    registered = False

    def register(self, registry: APIRouter) -> None:
        self.registered = True
        registry.add_api_route("/registered", self.endpoint, methods=["GET"])

    async def endpoint(self) -> dict[str, bool]:
        return {"ok": True}


class BodyPayload(BaseModel):
    value: str


class DisposableFlag(Protocol):
    disposed: bool


class FakePostController:
    def __init__(self, *, path: str) -> None:
        self._path = path
        self.called = False
        self.registered = False

    def register(self, registry: APIRouter) -> None:
        self.registered = True
        registry.add_api_route(self._path, self.endpoint, methods=["POST"])

    async def endpoint(self, body: BodyPayload) -> dict[str, bool]:
        self.called = True
        return {"ok": bool(body.value)}


class PassingIPThrottlerFactory:
    def __init__(self) -> None:
        self.disposed = False

    def __call__(self, *, quota: object) -> Callable[[Request], Awaitable[None]]:
        return self.throttle

    async def throttle(self, request: Request) -> None:
        return None

    async def dispose(self) -> None:
        self.disposed = True


class RejectingIPThrottlerFactory:
    def __init__(self) -> None:
        self.called_paths: list[str] = []
        self.disposed = False

    def __call__(self, *, quota: object) -> Callable[[Request], Awaitable[None]]:
        return self.throttle

    async def throttle(self, request: Request) -> None:
        self.called_paths.append(request.url.path)
        raise HTTPException(
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            detail="Too many requests",
        )

    async def dispose(self) -> None:
        self.disposed = True


def test_fastapi_factory_disables_docs_and_optional_middlewares_in_production() -> None:
    instrumentor = FakeTelemetryInstrumentor()
    controllers = [FakeController() for _ in range(8)]
    app = _build_factory(
        application_settings=ApplicationSettings(environment=Environment.PRODUCTION),
        instrumentor=instrumentor,
        controllers=controllers,
    )(
        add_trusted_hosts_middleware=False,
        add_cors_middleware=False,
    )

    assert app.docs_url is None
    middleware_names = {cast(Any, middleware.cls).__name__ for middleware in app.user_middleware}
    assert middleware_names == {PreBodyIPThrottlingMiddleware.__name__}
    assert instrumentor.instrumented_app is app
    assert all(controller.registered for controller in controllers)


def test_fastapi_factory_adds_docs_and_default_middlewares_outside_production() -> None:
    app = _build_factory(
        application_settings=ApplicationSettings(environment=Environment.DEVELOPMENT),
        instrumentor=FakeTelemetryInstrumentor(),
    )()

    middleware_names = {cast(Any, middleware.cls).__name__ for middleware in app.user_middleware}
    assert app.docs_url == "/docs"
    assert TrustedHostMiddleware.__name__ in middleware_names
    assert CORSMiddleware.__name__ in middleware_names
    assert PreBodyIPThrottlingMiddleware.__name__ in middleware_names


def test_fastapi_factory_rejects_invalid_hosts_before_pre_body_ip_throttling() -> None:
    ip_throttler_factory = RejectingIPThrottlerFactory()
    app = _build_factory(
        application_settings=ApplicationSettings(environment=Environment.DEVELOPMENT),
        instrumentor=FakeTelemetryInstrumentor(),
        ip_throttler_factory=cast(IPThrottlerFactory, ip_throttler_factory),
    )(
        add_cors_middleware=False,
    )

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/users",
            content="{",
            headers={"content-type": "application/json", "host": "invalid.test"},
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert ip_throttler_factory.called_paths == []


def test_fastapi_factory_applies_pre_body_ip_throttling_to_post_routes() -> None:
    ip_throttler_factory = RejectingIPThrottlerFactory()
    post_controllers = _post_controllers()
    app = _build_factory(
        application_settings=ApplicationSettings(environment=Environment.DEVELOPMENT),
        instrumentor=FakeTelemetryInstrumentor(),
        controllers=[
            FakeController(),
            FakeController(),
            post_controllers[0],
            post_controllers[1],
            post_controllers[2],
            post_controllers[3],
            FakeController(),
            FakeController(),
        ],
        ip_throttler_factory=cast(IPThrottlerFactory, ip_throttler_factory),
    )(
        add_trusted_hosts_middleware=False,
        add_cors_middleware=False,
    )

    with TestClient(app) as test_client:
        responses = [
            test_client.post(
                path,
                content="{",
                headers={"content-type": "application/json"},
            )
            for path in PRE_BODY_THROTTLED_POST_PATHS
        ]

    assert {response.status_code for response in responses} == {HTTPStatus.TOO_MANY_REQUESTS}
    assert ip_throttler_factory.called_paths == list(PRE_BODY_THROTTLED_POST_PATHS)
    assert not any(controller.called for controller in post_controllers)


def test_fastapi_factory_disposes_runtime_resources_on_shutdown() -> None:
    session_factory = FakeSessionFactory()
    ip_throttler_factory = PassingIPThrottlerFactory()
    app = _build_factory(
        application_settings=ApplicationSettings(environment=Environment.DEVELOPMENT),
        instrumentor=FakeTelemetryInstrumentor(),
        session_factory=cast(SQLAlchemySessionFactory, session_factory),
        ip_throttler_factory=cast(IPThrottlerFactory, ip_throttler_factory),
    )(
        add_trusted_hosts_middleware=False,
        add_cors_middleware=False,
    )

    with TestClient(app):
        assert not _is_disposed(session_factory)
        assert not _is_disposed(ip_throttler_factory)

    assert _is_disposed(session_factory)
    assert _is_disposed(ip_throttler_factory)


def _build_factory(
    *,
    application_settings: ApplicationSettings,
    instrumentor: FakeTelemetryInstrumentor,
    controllers: Sequence[FakeController | FakePostController] | None = None,
    ip_throttler_factory: IPThrottlerFactory | None = None,
    session_factory: SQLAlchemySessionFactory | None = None,
) -> FastAPIFactory:
    (
        health_check_controller,
        health_check_websocket_controller,
        issue_token_controller,
        refresh_token_controller,
        revoke_token_controller,
        create_user_controller,
        current_user_controller,
        staff_user_lookup_controller,
    ) = controllers or [FakeController() for _ in range(8)]
    return FastAPIFactory(
        _application_settings=application_settings,
        _fastapi_settings=FastAPISettings(),
        _cors_settings=CORSSettings(),
        _telemetry_instrumentor=cast(OpenTelemetryInstrumentor, instrumentor),
        _session_factory=session_factory or cast(SQLAlchemySessionFactory, FakeSessionFactory()),
        _ip_throttler_factory=ip_throttler_factory
        or cast(IPThrottlerFactory, PassingIPThrottlerFactory()),
        _health_check_controller=cast(HealthCheckController, health_check_controller),
        _health_check_websocket_controller=cast(
            HealthCheckWebSocketController,
            health_check_websocket_controller,
        ),
        _issue_token_controller=cast(IssueTokenController, issue_token_controller),
        _refresh_token_controller=cast(RefreshTokenController, refresh_token_controller),
        _revoke_token_controller=cast(RevokeTokenController, revoke_token_controller),
        _create_user_controller=cast(CreateUserController, create_user_controller),
        _current_user_controller=cast(CurrentUserController, current_user_controller),
        _staff_user_lookup_controller=cast(
            StaffUserLookupController,
            staff_user_lookup_controller,
        ),
    )


def _is_disposed(disposable: DisposableFlag) -> bool:
    return bool(disposable.disposed)


def _post_controllers() -> list[FakePostController]:
    return [FakePostController(path=path) for path in PRE_BODY_THROTTLED_POST_PATHS]
