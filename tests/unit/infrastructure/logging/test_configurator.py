import logging
from typing import Any

import logfire
import pytest
from pydantic import SecretStr

from fastapi_template.infrastructure.logfire.configurator import LogfireSettings
from fastapi_template.infrastructure.logging.configurator import (
    LoggingConfigurator,
    LoggingSettings,
)


class FakeLogfireLoggingHandler(logging.Handler):
    pass


def test_logging_configurator_adds_logfire_handler_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_config: dict[str, Any] = {}
    monkeypatch.setattr(
        logfire,
        "LogfireLoggingHandler",
        FakeLogfireLoggingHandler,
    )
    monkeypatch.setattr(logging, "basicConfig", lambda **kwargs: captured_config.update(kwargs))

    configurator = LoggingConfigurator(
        _settings=LoggingSettings(
            logfire_settings=LogfireSettings(enabled=True, token=SecretStr("token")),
        ),
    )

    configurator.configure()

    handlers = captured_config["handlers"]
    assert any(isinstance(handler, FakeLogfireLoggingHandler) for handler in handlers)
