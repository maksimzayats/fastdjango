from typing import Any

import dj_database_url
from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from configs.application import (
    ApplicationSettings,
)
from configs.logging import LoggingSettings
from infrastructure.adapters.database.settings import DatabaseSettings
from infrastructure.adapters.s3.settings import AWSS3Settings
from infrastructure.frameworks.django.settings.pydantic_adapter import PydanticSettingsAdapter


class DjangoSettings(ApplicationSettings):
    language_code: str = "en-us"
    use_tz: bool = True
    installed_apps: tuple[str, ...] = (
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
        "core.user.apps.UserConfig",
    )


class DjangoHttpSettings(BaseSettings):
    root_urlconf: str = "delivery.http.django.urls"

    middleware: tuple[str, ...] = (
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    )


class DjangoAuthSettings(BaseSettings):
    auth_user_model: str = "user.User"
    authentication_backends: tuple[str, ...] = ("django.contrib.auth.backends.ModelBackend",)
    password_validators: tuple[dict[str, str], ...] = Field(
        default=(
            {
                "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
            },
            {
                "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
            },
            {
                "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
            },
            {
                "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
            },
        ),
        alias="auth_password_validators",
    )


class DjangoDatabaseSettings(DatabaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    default_auto_field: str = "django.db.models.BigAutoField"
    conn_max_age: int = 600

    @computed_field()
    def databases(self) -> dict[str, Any]:
        return {
            "default": dj_database_url.parse(
                self.url.get_secret_value(),
                conn_max_age=self.conn_max_age,
            ),
        }


class DjangoSecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DJANGO_")

    debug: bool = False
    secret_key: SecretStr


class DjangoStorageSettings(BaseSettings):
    static_url: str = "static/"
    media_url: str = "media/"

    s3_settings: AWSS3Settings = Field(default_factory=AWSS3Settings)  # type: ignore[arg-type]

    @computed_field()
    def storages(self) -> dict[str, Any]:
        base_options = {
            "access_key": self.s3_settings.access_key_id,
            "secret_key": self.s3_settings.secret_access_key.get_secret_value(),
            "endpoint_url": self.s3_settings.endpoint_url,
        }

        return {
            "staticfiles": {
                "BACKEND": "storages.backends.s3.S3Storage",
                "OPTIONS": {
                    **base_options,
                    "bucket_name": self.s3_settings.public_bucket_name,
                },
            },
            "default": {
                "BACKEND": "storages.backends.s3.S3Storage",
                "OPTIONS": {
                    **base_options,
                    "bucket_name": self.s3_settings.protected_bucket_name,
                },
            },
        }


class DjangoTemplatesSettings(BaseSettings):
    templates: tuple[dict[str, Any], ...] = (
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    "django.template.context_processors.debug",
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                ],
            },
        },
    )


adapter = PydanticSettingsAdapter()
adapter.adapt(
    DjangoSettings(),
    DjangoHttpSettings(),
    DjangoDatabaseSettings(),  # type: ignore[call-arg, missing-argument]
    DjangoAuthSettings(),
    DjangoSecuritySettings(),  # type: ignore[call-arg, missing-argument]
    DjangoStorageSettings(),
    DjangoTemplatesSettings(),
    LoggingSettings(),
    settings_locals=locals(),
)
