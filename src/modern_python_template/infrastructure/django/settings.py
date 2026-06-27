from typing import Any, Literal
from urllib.parse import urlsplit

import dj_database_url
from pydantic import Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

from modern_python_template.infrastructure.django.pydantic_settings_adapter import (
    PydanticSettingsAdapter,
)
from modern_python_template.infrastructure.django.stubs import patch_django_stubs
from modern_python_template.infrastructure.shared import ApplicationSettings

patch_django_stubs()


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
        "modern_python_template.core.authentication.apps.AuthenticationConfig",
        "modern_python_template.core.user.apps.UserConfig",
    )


class DjangoHttpSettings(BaseSettings):
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    csrf_trusted_origins: list[str] = Field(default_factory=lambda: ["http://localhost"])

    root_urlconf: str = "modern_python_template.entrypoints.django.urls"

    middleware: tuple[str, ...] = (
        "django.middleware.security.SecurityMiddleware",
        "whitenoise.middleware.WhiteNoiseMiddleware",
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
    # Django recommends disabling persistent connections under ASGI and using
    # backend pooling instead; our FastAPI request middleware closes old
    # connections at the HTTP boundary, while PgBouncer handles reuse.
    conn_max_age: int = 0
    # Docker routes app traffic through PgBouncer in transaction pooling mode.
    # Server-side cursors are bound to one server connection, so they are unsafe
    # when PgBouncer may move the next transaction to another connection.
    disable_server_side_cursors: bool = True
    test_name: str | None = None

    @computed_field()  # type: ignore[prop-decorator]
    @property
    def databases(self) -> dict[str, Any]:
        default_database = dj_database_url.parse(
            self.url.get_secret_value(),
            conn_max_age=self.conn_max_age,
        )
        default_database["DISABLE_SERVER_SIDE_CURSORS"] = self.disable_server_side_cursors

        if self.test_name is not None:
            default_database["TEST"] = {
                **default_database.get("TEST", {}),
                "NAME": self.test_name,
            }

        return {"default": default_database}


class DjangoSecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DJANGO_")

    debug: bool = False
    secret_key: SecretStr


class DjangoStorageSettings(BaseSettings):
    model_config = SettingsConfigDict(populate_by_name=True)

    storage_backend: Literal["local", "s3"] = Field(
        default="s3",
        validation_alias="STORAGE_BACKEND",
    )
    static_url: str = "/static/"
    static_root: str = "staticfiles"
    media_url: str = "/media/"
    media_root: str = "media"

    endpoint_url: str | None = Field(default=None, validation_alias="AWS_S3_ENDPOINT_URL")
    public_endpoint_url: str | None = Field(
        default=None,
        validation_alias="AWS_S3_PUBLIC_ENDPOINT_URL",
    )
    access_key_id: str | None = Field(default=None, validation_alias="AWS_S3_ACCESS_KEY_ID")
    secret_access_key: SecretStr | None = Field(
        default=None,
        validation_alias="AWS_S3_SECRET_ACCESS_KEY",
    )
    region_name: str | None = Field(default=None, validation_alias="AWS_S3_REGION_NAME")
    protected_bucket_name: str = Field(
        default="protected",
        validation_alias="AWS_S3_PROTECTED_BUCKET_NAME",
    )
    public_bucket_name: str = Field(
        default="public",
        validation_alias="AWS_S3_PUBLIC_BUCKET_NAME",
    )

    @computed_field()  # type: ignore[prop-decorator]
    @property
    def storages(self) -> dict[str, Any]:
        if self.storage_backend == "local":
            return {
                "staticfiles": {
                    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
                },
                "default": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                },
            }

        return self._build_s3_storages()

    def _build_s3_storages(self) -> dict[str, Any]:
        base_options = {
            "access_key": self._require_s3_setting(
                self.access_key_id,
                name="AWS_S3_ACCESS_KEY_ID",
            ),
            "secret_key": self._require_s3_secret(self.secret_access_key),
            "endpoint_url": self._require_s3_setting(
                self.endpoint_url,
                name="AWS_S3_ENDPOINT_URL",
            ),
        }

        if self.region_name is not None:
            base_options["region_name"] = self.region_name

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

    def _require_s3_setting(self, value: str | None, *, name: str) -> str:
        if value is None or value == "":
            msg = f"{name} is required when STORAGE_BACKEND=s3."
            raise ValueError(msg)

        return value

    def _require_s3_secret(self, value: SecretStr | None) -> str:
        if value is None or value.get_secret_value() == "":
            msg = "AWS_S3_SECRET_ACCESS_KEY is required when STORAGE_BACKEND=s3."
            raise ValueError(msg)

        return value.get_secret_value()

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
    DjangoDatabaseSettings(),  # type: ignore[call-arg]
    DjangoAuthSettings(),
    DjangoSecuritySettings(),  # type: ignore[call-arg]
    DjangoStorageSettings(),
    DjangoTemplatesSettings(),
    settings_locals=locals(),
)
