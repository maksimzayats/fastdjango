import logging.config
import os

import django
import django_stubs_ext
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class DjangoConfigurator:
    def configure(self, django_settings_module: str) -> None:
        self._load_dotenv()
        self._setup(django_settings_module=django_settings_module)

        logger.info("Django has been configured successfully.")

    def _load_dotenv(self) -> None:
        load_dotenv(override=False)

    def _setup(self, django_settings_module: str) -> None:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", django_settings_module)
        django_stubs_ext.monkeypatch()
        django.setup()
