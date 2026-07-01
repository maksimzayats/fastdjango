from typing import Any

import pytest
from pydantic import SecretStr

from fastapi_template.infrastructure.logfire.configurator import (
    LogfireConfigurator,
    LogfireSettings,
)


def test_logfire_settings_require_enabled_flag_and_token() -> None:
    assert LogfireSettings(enabled=False, token=SecretStr("token")).is_enabled is False
    assert LogfireSettings(enabled=True, token=None).is_enabled is False
    assert LogfireSettings(enabled=True, token=SecretStr("token")).is_enabled is True


def test_logfire_configurator_skips_disabled_logfire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "fastapi_template.infrastructure.logfire.configurator.logfire_client.configure",
        lambda **kwargs: configure_calls.append(kwargs),
    )

    configurator = LogfireConfigurator(
        _logfire_settings=LogfireSettings(enabled=False, token=SecretStr("token")),
    )

    configurator.configure()

    assert configure_calls == []


def test_logfire_configurator_configures_enabled_logfire(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "fastapi_template.infrastructure.logfire.configurator.logfire_client.configure",
        lambda **kwargs: configure_calls.append(kwargs),
    )

    configurator = LogfireConfigurator(
        _logfire_settings=LogfireSettings(
            enabled=True,
            service_name="service",
            service_version="1.2.3",
            environment="test",
            token=SecretStr(_secret_value()),
        ),
    )

    configurator.configure()

    assert len(configure_calls) == 1
    assert configure_calls[0]["service_name"] == "service"
    assert configure_calls[0]["service_version"] == "1.2.3"
    assert configure_calls[0]["environment"] == "test"
    assert configure_calls[0]["token"] == _secret_value()
    assert configure_calls[0]["scrubbing"].extra_patterns == [
        "access_token",
        "refresh_token",
    ]


def _secret_value() -> str:
    return "secret-token"
