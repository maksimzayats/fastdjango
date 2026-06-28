from typing import Any

import pytest
from fastapi import FastAPI
from pydantic import SecretStr

from fastapi_template.infrastructure.logfire.configurator import LogfireSettings
from fastapi_template.infrastructure.logfire.instrumentor import (
    InstrumentorSettings,
    OpenTelemetryInstrumentor,
)


def test_open_telemetry_instrumentor_skips_disabled_logfire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "fastapi_template.infrastructure.logfire.instrumentor.logfire.instrument_requests",
        lambda: calls.append("requests"),
    )
    instrumentor = _build_instrumentor(logfire_settings=LogfireSettings(enabled=False))

    instrumentor.instrument_libraries()
    instrumentor.instrument_fastapi(app=FastAPI())

    assert calls == []


def test_open_telemetry_instrumentor_instruments_enabled_libraries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        "fastapi_template.infrastructure.logfire.instrumentor.logfire.instrument_requests",
        lambda: calls.append(("requests", {})),
    )
    monkeypatch.setattr(
        "fastapi_template.infrastructure.logfire.instrumentor.logfire.instrument_psycopg",
        lambda **kwargs: calls.append(("psycopg", kwargs)),
    )
    monkeypatch.setattr(
        "fastapi_template.infrastructure.logfire.instrumentor.logfire.instrument_httpx",
        lambda: calls.append(("httpx", {})),
    )
    monkeypatch.setattr(
        "fastapi_template.infrastructure.logfire.instrumentor.logfire.instrument_redis",
        lambda: calls.append(("redis", {})),
    )
    monkeypatch.setattr(
        "fastapi_template.infrastructure.logfire.instrumentor.logfire.instrument_pydantic",
        lambda: calls.append(("pydantic", {})),
    )
    instrumentor = _build_instrumentor()

    instrumentor.instrument_libraries()

    assert [call_name for call_name, _kwargs in calls] == [
        "requests",
        "psycopg",
        "httpx",
        "redis",
        "pydantic",
    ]
    assert calls[1][1]["enable_commenter"] is True
    assert calls[1][1]["commenter_options"]["db_driver"] is True
    assert calls[1][1]["commenter_options"]["dbapi_level"] is True


def test_open_telemetry_instrumentor_instruments_enabled_fastapi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "fastapi_template.infrastructure.logfire.instrumentor.logfire.instrument_fastapi",
        lambda app, **kwargs: calls.append({"app": app, **kwargs}),
    )
    app = FastAPI()
    instrumentor = _build_instrumentor(
        instrumentor_settings=InstrumentorSettings(
            fastapi_excluded_urls=["/health"],
        ),
    )

    instrumentor.instrument_fastapi(app=app)

    assert calls == [{"app": app, "excluded_urls": ["/health"]}]


def _build_instrumentor(
    *,
    instrumentor_settings: InstrumentorSettings | None = None,
    logfire_settings: LogfireSettings | None = None,
) -> OpenTelemetryInstrumentor:
    return OpenTelemetryInstrumentor(
        _instrumentor_settings=instrumentor_settings or InstrumentorSettings(),
        _logfire_settings=logfire_settings
        or LogfireSettings(enabled=True, token=SecretStr("token")),
    )
