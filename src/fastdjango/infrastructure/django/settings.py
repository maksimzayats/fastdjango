from typing import Any
from urllib.parse import urlsplit

import dj_database_url
from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastdjango.infrastructure.django.pydantic_settings_adapter import PydanticSettingsAdapter
from fastdjango.infrastructure.shared import ApplicationSettings


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
        "fastdjango.core.authentication.apps.AuthenticationConfig",
        "fastdjango.core.user.apps.UserConfig",
    )


class DjangoHttpSettings(BaseSettings):
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    csrf_trusted_origins: list[str] = Field(default_factory=lambda: ["http://localhost"])

    root_urlconf: str = "fastdjango.entrypoints.django.urls"

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


class DjangoDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: SecretStr
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
    model_config = SettingsConfigDict(populate_by_name=True)

    static_url: str = "/static/"
    media_url: str = "/media/"

    endpoint_url: str = Field(validation_alias="AWS_S3_ENDPOINT_URL")
    public_endpoint_url: str | None = Field(
        default=None,
        validation_alias="AWS_S3_PUBLIC_ENDPOINT_URL",
    )
    access_key_id: str = Field(validation_alias="AWS_S3_ACCESS_KEY_ID")
    secret_access_key: SecretStr = Field(validation_alias="AWS_S3_SECRET_ACCESS_KEY")
    protected_bucket_name: str = Field(
        default="protected",
        validation_alias="AWS_S3_PROTECTED_BUCKET_NAME",
    )
    public_bucket_name: str = Field(
        default="public",
        validation_alias="AWS_S3_PUBLIC_BUCKET_NAME",
    )

    @computed_field()
    def storages(self) -> dict[str, Any]:
        base_options = {
            "access_key": self.access_key_id,
            "secret_key": self.secret_access_key.get_secret_value(),
            "endpoint_url": self.endpoint_url,
        }

        return {
            "staticfiles": {
                "BACKEND": "storages.backends.s3.S3Storage",
                "OPTIONS": self._build_staticfiles_options(base_options=base_options),
            },
            "default": {
                "BACKEND": "storages.backends.s3.S3Storage",
                "OPTIONS": {
                    **base_options,
                    "bucket_name": self.protected_bucket_name,
                },
            },
        }

    def _build_staticfiles_options(self, *, base_options: dict[str, Any]) -> dict[str, Any]:
        options = {
            **base_options,
            "bucket_name": self.public_bucket_name,
        }

        public_url_options = self._build_public_static_url_options()
        if public_url_options:
            options.update(public_url_options)

        return options

    def _build_public_static_url_options(self) -> dict[str, str]:
        if not self.public_endpoint_url:
            return {}

        endpoint = urlsplit(self.public_endpoint_url)
        if not endpoint.scheme or not endpoint.netloc:
            return {}

        custom_domain = endpoint.netloc
        endpoint_path = endpoint.path.strip("/")
        if endpoint_path:
            custom_domain = f"{custom_domain}/{endpoint_path}"

        bucket_suffix = f"/{self.public_bucket_name}"
        if not custom_domain.endswith(bucket_suffix):
            custom_domain = f"{custom_domain}/{self.public_bucket_name}"

        return {
            "custom_domain": custom_domain,
            "url_protocol": f"{endpoint.scheme}:",
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
    DjangoStorageSettings(),  # type: ignore[call-arg, missing-argument]
    DjangoTemplatesSettings(),
    settings_locals=locals(),
)
