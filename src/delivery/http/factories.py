from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from a2wsgi import WSGIMiddleware
from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from configs.application import ApplicationSettings, Environment
from delivery.http.django.factories import DjangoWSGIFactory
from delivery.http.health.controllers import HealthController
from delivery.http.settings import CORSSettings, HTTPSettings
from delivery.http.user.controllers import UserController, UserTokenController
from infrastructure.anyio.configurator import AnyIOConfigurator
from infrastructure.telemetry.configurator import LogfireConfigurator
from infrastructure.telemetry.instrumentor import OpenTelemetryInstrumentor


@dataclass
class Lifespan:
    _application_settings: ApplicationSettings
    _anyio_configurator: AnyIOConfigurator
    _logfire_configurator: LogfireConfigurator

    @asynccontextmanager
    async def __call__(self, _app: FastAPI) -> AsyncIterator[None]:
        self._anyio_configurator.configure()
        self._logfire_configurator.configure(
            service_name="fastapi",
            service_version=self._application_settings.version,
            environment=self._application_settings.environment,
        )

        yield


@dataclass
class FastAPIFactory:
    _application_settings: ApplicationSettings
    _http_settings: HTTPSettings
    _cors_settings: CORSSettings
    _telemetry_instrumentor: OpenTelemetryInstrumentor
    _lifespan: Lifespan
    _django_wsgi_factory: DjangoWSGIFactory
    _health_controller: HealthController
    _user_token_controller: UserTokenController
    _user_controller: UserController

    def __call__(
        self,
        *,
        include_django: bool = True,
        add_trusted_hosts_middleware: bool = True,
        add_cors_middleware: bool = True,
    ) -> FastAPI:
        docs_url = (
            "/api/docs"
            if self._application_settings.environment != Environment.PRODUCTION
            else None
        )

        app = FastAPI(
            title="API",
            lifespan=self._lifespan,
            docs_url=docs_url,
            redoc_url=None,
        )

        self._telemetry_instrumentor.instrument_fastapi(app=app)

        if add_trusted_hosts_middleware:
            app.add_middleware(
                TrustedHostMiddleware,  # type: ignore[invalid-argument-type]
                allowed_hosts=self._http_settings.allowed_hosts,
            )

        if add_cors_middleware:
            app.add_middleware(
                CORSMiddleware,  # type: ignore[invalid-argument-type]
                allow_origins=self._cors_settings.allow_origins,
                allow_credentials=self._cors_settings.allow_credentials,
                allow_methods=self._cors_settings.allow_methods,
                allow_headers=self._cors_settings.allow_headers,
            )

        api_router = APIRouter(prefix="/api")
        self._health_controller.register(api_router)
        self._user_controller.register(api_router)
        self._user_token_controller.register(api_router)
        app.include_router(api_router)

        if include_django:
            django_wsgi = self._django_wsgi_factory()
            app.mount("/django", WSGIMiddleware(django_wsgi))  # type: ignore[arg-type, invalid-argument-type]

        return app
