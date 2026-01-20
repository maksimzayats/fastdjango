import logging
from typing import Any

from pydantic import SecretBytes, SecretStr
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class PydanticSettingsAdapter:
    def adapt(
        self,
        *settings: BaseSettings,
        settings_locals: dict[str, Any],
    ) -> None:
        for setting in settings:
            self._adapt(settings=setting, settings_locals=settings_locals)

    def _adapt(
        self,
        settings: BaseSettings,
        settings_locals: dict[str, Any],
    ) -> None:
        for key, value in settings.model_dump(by_alias=True).items():
            resolved_key = self._resolve_key(key)
            resolved_value = self._resolve_value(value)
            settings_locals[resolved_key] = resolved_value

    def _resolve_key(self, key: str) -> str:
        return key.upper()

    def _resolve_value(self, value: Any) -> Any:
        if isinstance(value, (SecretStr, SecretBytes)):
            return value.get_secret_value()

        return value
