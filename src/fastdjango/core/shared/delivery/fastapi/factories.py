from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from a2wsgi import WSGIMiddleware
from fastapi import APIRouter, FastAPI
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from fastdjango.core.authentication.delivery.fastapi.controllers import (
    AuthenticationTokenController,
)
from fastdjango.core.health.delivery.fastapi.controllers import HealthController
from fastdjango.core.shared.delivery.django.factories import DjangoWSGIFactory
from fastdjango.core.user.delivery.fastapi.controllers import UserController
from fastdjango.infrastructure.anyio.configurator import AnyIOConfigurator
from fastdjango.infrastructure.logfire.instrumentor import OpenTelemetryInstrumentor
from fastdjango.infrastructure.shared import ApplicationSettings, Environment


class FastAPISettings(BaseSettings):
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])


class CORSSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CORS_")

    allow_credentials: bool = True
    allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost"])
    allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    allow_headers: list[str] = Field(default_factory=lambda: ["*"])


@dataclass(kw_only=True)
class Lifespan:
    _anyio_configurator: AnyIOConfigurator

    @asynccontextmanager
    async def __call__(self, _app: FastAPI) -> AsyncIterator[None]:
        self._anyio_configurator.configure()

        yield


@dataclass(kw_only=True)
class FastAPIFactory:
    _application_settings: ApplicationSettings
    _fastapi_settings: FastAPISettings
    _cors_settings: CORSSettings

    _lifespan: Lifespan
    _telemetry_instrumentor: OpenTelemetryInstrumentor
    _django_wsgi_factory: DjangoWSGIFactory

    _health_controller: HealthController
    _authentication_token_controller: AuthenticationTokenController
    _user_controller: UserController

    def __call__(
        self,
        *,
        include_django: bool = True,
        add_trusted_hosts_middleware: bool = True,
        add_cors_middleware: bool = True,
    ) -> FastAPI:
        docs_url = (
            "/docs" if self._application_settings.environment != Environment.PRODUCTION else None
        )

        app = FastAPI(
            title="API",
            lifespan=self._lifespan,
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

        if include_django:
            django_wsgi = self._django_wsgi_factory()
            app.mount("/django", WSGIMiddleware(django_wsgi))  # type: ignore[arg-type, invalid-argument-type]

        return app

    def _add_middlewares(
        self,
        app: FastAPI,
        *,
        add_trusted_hosts_middleware: bool = True,
        add_cors_middleware: bool = True,
    ) -> None:
        if add_trusted_hosts_middleware:
            app.add_middleware(
                TrustedHostMiddleware,  # type: ignore[invalid-argument-type]
                allowed_hosts=self._fastapi_settings.allowed_hosts,
            )

        if add_cors_middleware:
            app.add_middleware(
                CORSMiddleware,  # type: ignore[invalid-argument-type]
                allow_origins=self._cors_settings.allow_origins,
                allow_credentials=self._cors_settings.allow_credentials,
                allow_methods=self._cors_settings.allow_methods,
                allow_headers=self._cors_settings.allow_headers,
            )

    def _register_controllers(
        self,
        app: FastAPI,
    ) -> None:
        health_router = APIRouter(tags=["health"])
        self._health_controller.register(health_router)
        app.include_router(health_router)

        auth_router = APIRouter(tags=["auth", "token"])
        self._authentication_token_controller.register(auth_router)
        app.include_router(auth_router)

        user_router = APIRouter(tags=["user"])
        self._user_controller.register(user_router)
        app.include_router(user_router)
