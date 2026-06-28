from typing import Any, cast

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

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


class FakeTelemetryInstrumentor:
    instrumented_app: FastAPI | None = None

    def instrument_fastapi(self, *, app: FastAPI) -> None:
        self.instrumented_app = app


class FakeController:
    registered = False

    def register(self, registry: APIRouter) -> None:
        self.registered = True
        registry.add_api_route("/registered", self.endpoint, methods=["GET"])

    async def endpoint(self) -> dict[str, bool]:
        return {"ok": True}


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
    assert app.user_middleware == []
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


def _build_factory(
    *,
    application_settings: ApplicationSettings,
    instrumentor: FakeTelemetryInstrumentor,
    controllers: list[FakeController] | None = None,
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
