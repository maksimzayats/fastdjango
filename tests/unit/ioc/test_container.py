from typing import cast

import pytest
from diwire import Container

from fastapi_template.infrastructure.logfire.configurator import LogfireConfigurator
from fastapi_template.infrastructure.logfire.instrumentor import OpenTelemetryInstrumentor
from fastapi_template.infrastructure.logging.configurator import LoggingConfigurator
from fastapi_template.ioc import container as container_module


class FakeResolver:
    def __init__(self, *, dependency: object) -> None:
        self._dependency = dependency

    def resolve(self, _dependency_type: object) -> object:
        return self._dependency


class FakeConfigurator:
    configured = False

    def configure(self) -> None:
        self.configured = True


class FakeInstrumentor:
    instrumented = False

    def instrument_libraries(self) -> None:
        self.instrumented = True


def test_get_container_runs_enabled_composition_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        container_module,
        "_configure_logging",
        lambda _container: calls.append("logging"),
    )
    monkeypatch.setattr(
        container_module,
        "_configure_logfire",
        lambda _container: calls.append("logfire"),
    )
    monkeypatch.setattr(
        container_module,
        "_instrument_libraries",
        lambda _container: calls.append("instrument"),
    )
    monkeypatch.setattr(
        container_module,
        "register_dependencies",
        lambda _container: calls.append("register"),
    )

    result = container_module.get_container()

    assert isinstance(result, Container)
    assert calls == ["register", "logging", "logfire", "instrument"]


def test_get_container_skips_disabled_composition_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        container_module,
        "_configure_logging",
        lambda _container: calls.append("logging"),
    )
    monkeypatch.setattr(
        container_module,
        "_configure_logfire",
        lambda _container: calls.append("logfire"),
    )
    monkeypatch.setattr(
        container_module,
        "_instrument_libraries",
        lambda _container: calls.append("instrument"),
    )
    monkeypatch.setattr(
        container_module,
        "register_dependencies",
        lambda _container: calls.append("register"),
    )

    container_module.get_container(
        configure_logging=False,
        configure_logfire=False,
        instrument_libraries=False,
    )

    assert calls == ["register"]


def test_configure_logging_resolves_and_runs_configurator() -> None:
    configurator = FakeConfigurator()

    container_module._configure_logging(  # noqa: SLF001
        cast(Container, FakeResolver(dependency=cast(LoggingConfigurator, configurator))),
    )

    assert configurator.configured is True


def test_configure_logfire_resolves_and_runs_configurator() -> None:
    configurator = FakeConfigurator()

    container_module._configure_logfire(  # noqa: SLF001
        cast(Container, FakeResolver(dependency=cast(LogfireConfigurator, configurator))),
    )

    assert configurator.configured is True


def test_instrument_libraries_resolves_and_runs_instrumentor() -> None:
    instrumentor = FakeInstrumentor()

    container_module._instrument_libraries(  # noqa: SLF001
        cast(Container, FakeResolver(dependency=cast(OpenTelemetryInstrumentor, instrumentor))),
    )

    assert instrumentor.instrumented is True
