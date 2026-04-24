import logging
from dataclasses import dataclass

import logfire
from logfire import ScrubbingOptions
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastdjango.infrastructure.configurators import BaseConfigurator

logger = logging.getLogger(__name__)


class LogfireSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LOGFIRE_")

    enabled: bool = False
    service_name: str = "fastdjango"
    service_version: str = "0.1.0"
    environment: str = "production"

    token: SecretStr | None = None

    @property
    def is_enabled(self) -> bool:
        return self.enabled and self.token is not None


@dataclass(kw_only=True)
class LogfireConfigurator(BaseConfigurator):
    _logfire_settings: LogfireSettings

    def configure(self) -> None:
        if not self._logfire_settings.is_enabled:
            logger.debug("Logfire is disabled; skipping configuration")
            return

        logfire.configure(
            service_name=self._logfire_settings.service_name,
            service_version=self._logfire_settings.service_version,
            environment=self._logfire_settings.environment,
            token=self._logfire_settings.token.get_secret_value(),  # type: ignore[union-attr, possibly-missing-attribute]
            scrubbing=ScrubbingOptions(
                extra_patterns=[
                    "access_token",
                    "refresh_token",
                ],
            ),
        )

        logger.info(
            "Logfire has been configured for service: %s",
            self._logfire_settings.service_name,
        )
