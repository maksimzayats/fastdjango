from __future__ import annotations

import pytest

from modern_python_template.infrastructure.django.settings import DjangoStorageSettings


def test_storage_settings_use_whitenoise_for_local_filesystem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    _clear_s3_environment(monkeypatch=monkeypatch)

    settings = DjangoStorageSettings()

    assert settings.storages == {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
    }


def test_storage_settings_use_minio_s3_options(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_s3_environment(
        monkeypatch=monkeypatch,
        endpoint_url="http://localhost:9000",
        public_endpoint_url="http://localhost:9000",
        region_name="us-east-1",
    )

    settings = DjangoStorageSettings()

    assert settings.storages["staticfiles"]["OPTIONS"] == {
        "access_key": "access-key",
        "secret_key": "secret-key",
        "endpoint_url": "http://localhost:9000",
        "region_name": "us-east-1",
        "bucket_name": "public",
        "custom_domain": "localhost:9000/public",
        "url_protocol": "http:",
    }
    assert settings.storages["default"]["OPTIONS"] == {
        "access_key": "access-key",
        "secret_key": "secret-key",
        "endpoint_url": "http://localhost:9000",
        "region_name": "us-east-1",
        "bucket_name": "protected",
    }


def test_storage_settings_use_remote_s3_options(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_s3_environment(
        monkeypatch=monkeypatch,
        endpoint_url="https://storage.example.com",
        public_endpoint_url="https://assets.example.com/static",
        region_name="eu-central-1",
    )

    settings = DjangoStorageSettings()

    assert settings.storages["staticfiles"]["OPTIONS"]["endpoint_url"] == (
        "https://storage.example.com"
    )
    assert settings.storages["staticfiles"]["OPTIONS"]["custom_domain"] == (
        "assets.example.com/static/public"
    )
    assert settings.storages["default"]["OPTIONS"]["region_name"] == "eu-central-1"


def _set_s3_environment(
    *,
    monkeypatch: pytest.MonkeyPatch,
    endpoint_url: str,
    public_endpoint_url: str,
    region_name: str,
) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "s3")
    monkeypatch.setenv("AWS_S3_ENDPOINT_URL", endpoint_url)
    monkeypatch.setenv("AWS_S3_PUBLIC_ENDPOINT_URL", public_endpoint_url)
    monkeypatch.setenv("AWS_S3_ACCESS_KEY_ID", "access-key")
    monkeypatch.setenv("AWS_S3_SECRET_ACCESS_KEY", "secret-key")
    monkeypatch.setenv("AWS_S3_REGION_NAME", region_name)
    monkeypatch.setenv("AWS_S3_PUBLIC_BUCKET_NAME", "public")
    monkeypatch.setenv("AWS_S3_PROTECTED_BUCKET_NAME", "protected")


def _clear_s3_environment(*, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "AWS_S3_ENDPOINT_URL",
        "AWS_S3_PUBLIC_ENDPOINT_URL",
        "AWS_S3_ACCESS_KEY_ID",
        "AWS_S3_SECRET_ACCESS_KEY",
        "AWS_S3_REGION_NAME",
        "AWS_S3_PUBLIC_BUCKET_NAME",
        "AWS_S3_PROTECTED_BUCKET_NAME",
    ):
        monkeypatch.delenv(name, raising=False)
