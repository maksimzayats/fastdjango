from dataclasses import dataclass

import logfire
from diwire import Injected
from fastapi import FastAPI
from logfire.integrations.psycopg import CommenterOptions
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi_template.infrastructure.logfire.configurator import LogfireSettings


class InstrumentorSettings(BaseSettings):
    """OpenTelemetry instrumentation settings for supported libraries."""

    model_config = SettingsConfigDict(env_prefix="INSTRUMENTOR_")

    fastapi_excluded_urls: list[str] = Field(
        default_factory=lambda: [".*/api/v1/health"],
    )


@dataclass(kw_only=True)
class OpenTelemetryInstrumentor:
    """Register Logfire instrumentation for libraries and FastAPI apps."""

    _instrumentor_settings: Injected[InstrumentorSettings]
    _logfire_settings: Injected[LogfireSettings]

    def instrument_libraries(self) -> None:
        """Enable telemetry hooks for outbound clients and data libraries."""
        if not self._logfire_settings.is_enabled:
            return

        logfire.instrument_requests()
        logfire.instrument_psycopg(
            enable_commenter=True,
            commenter_options=CommenterOptions(
                db_driver=True,
                dbapi_level=True,
            ),
        )
        logfire.instrument_httpx()
        logfire.instrument_redis()
        logfire.instrument_pydantic()

    def instrument_fastapi(self, app: FastAPI) -> None:
        """Attach FastAPI request instrumentation to an application instance."""
        if not self._logfire_settings.is_enabled:
            return

        logfire.instrument_fastapi(
            app,
            excluded_urls=self._instrumentor_settings.fastapi_excluded_urls,
        )
