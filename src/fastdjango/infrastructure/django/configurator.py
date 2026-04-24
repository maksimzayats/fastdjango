import logging
import os
from dataclasses import dataclass

import django
import django_stubs_ext
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class DjangoConfiguratorSettings(BaseSettings):
    django_settings_module: str = "fastdjango.infrastructure.django.settings"


@dataclass(frozen=True, kw_only=True)
class DjangoConfigurator:
    _settings: DjangoConfiguratorSettings

    def configure(self) -> None:
        self._load_dotenv()
        self._setup()

        logger.info("Django has been configured successfully.")

    def _load_dotenv(self) -> None:
        load_dotenv(override=False)

    def _setup(self) -> None:
        os.environ.setdefault(
            "DJANGO_SETTINGS_MODULE",
            self._settings.django_settings_module,
        )
        django_stubs_ext.monkeypatch()
        django.setup()
