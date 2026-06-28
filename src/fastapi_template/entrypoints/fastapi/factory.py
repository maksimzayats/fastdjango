from dataclasses import dataclass

import fastapi
from diwire import Injected
from starlette.middleware import cors, trustedhost

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
from fastapi_template.entrypoints.fastapi.settings.cors import CORSSettings
from fastapi_template.entrypoints.fastapi.settings.fastapi import FastAPISettings
from fastapi_template.foundation.factory import BaseFactory
from fastapi_template.infrastructure.environment import Environment
from fastapi_template.infrastructure.logfire.instrumentor import OpenTelemetryInstrumentor
from fastapi_template.infrastructure.settings import ApplicationSettings


@dataclass(kw_only=True)
class FastAPIFactory(BaseFactory):
    """Define FastAPIFactory."""

    _application_settings: Injected[ApplicationSettings]
    _fastapi_settings: Injected[FastAPISettings]
    _cors_settings: Injected[CORSSettings]

    _telemetry_instrumentor: Injected[OpenTelemetryInstrumentor]

    _health_check_controller: Injected[HealthCheckController]
    _health_check_websocket_controller: Injected[HealthCheckWebSocketController]
    _issue_token_controller: Injected[IssueTokenController]
    _refresh_token_controller: Injected[RefreshTokenController]
    _revoke_token_controller: Injected[RevokeTokenController]
    _create_user_controller: Injected[CreateUserController]
    _current_user_controller: Injected[CurrentUserController]
    _staff_user_lookup_controller: Injected[StaffUserLookupController]

    def __call__(
        self,
        *,
        add_trusted_hosts_middleware: bool = True,
        add_cors_middleware: bool = True,
    ) -> fastapi.FastAPI:
        """Run call.

        Returns:
        The operation result.
        """
        docs_url: str | None = None
        if self._application_settings.environment is not Environment.PRODUCTION:
            docs_url = "/docs"

        app = fastapi.FastAPI(
            title="API",
            docs_url=docs_url,
            redoc_url=None,
        )

        self._telemetry_instrumentor.instrument_fastapi(app=app)
        self._add_middlewares(
            app=app,
            add_trusted_hosts_middleware=add_trusted_hosts_middleware,
            add_cors_middleware=add_cors_middleware,
        )
        self._register_controllers(app=app)

        return app

    def _add_middlewares(
        self,
        app: fastapi.FastAPI,
        *,
        add_trusted_hosts_middleware: bool = True,
        add_cors_middleware: bool = True,
    ) -> None:
        if add_trusted_hosts_middleware:
            app.add_middleware(
                trustedhost.TrustedHostMiddleware,
                allowed_hosts=self._fastapi_settings.allowed_hosts,
            )

        if add_cors_middleware:
            app.add_middleware(
                cors.CORSMiddleware,
                allow_origins=self._cors_settings.allow_origins,
                allow_credentials=self._cors_settings.allow_credentials,
                allow_methods=self._cors_settings.allow_methods,
                allow_headers=self._cors_settings.allow_headers,
            )

    def _register_controllers(
        self,
        app: fastapi.FastAPI,
    ) -> None:
        self._register_health_controller(app=app)
        self._register_authentication_controllers(app=app)
        self._register_user_controllers(app=app)

    def _register_health_controller(self, *, app: fastapi.FastAPI) -> None:
        health_router = fastapi.APIRouter(tags=["health"])
        self._health_check_controller.register(health_router)
        self._health_check_websocket_controller.register(health_router)
        app.include_router(health_router)

    def _register_authentication_controllers(self, *, app: fastapi.FastAPI) -> None:
        auth_router = fastapi.APIRouter(tags=["auth", "token"])
        self._issue_token_controller.register(auth_router)
        self._refresh_token_controller.register(auth_router)
        self._revoke_token_controller.register(auth_router)
        app.include_router(auth_router)

    def _register_user_controllers(self, *, app: fastapi.FastAPI) -> None:
        user_router = fastapi.APIRouter(tags=["user"])
        self._create_user_controller.register(user_router)
        self._current_user_controller.register(user_router)
        self._staff_user_lookup_controller.register(user_router)
        app.include_router(user_router)
