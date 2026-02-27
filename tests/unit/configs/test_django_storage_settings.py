from typing import Any

from pydantic import SecretStr

from configs.django import DjangoStorageSettings
from infrastructure.adapters.s3.settings import AWSS3Settings


def _get_static_options(settings: DjangoStorageSettings) -> dict[str, Any]:
    storages = settings.model_dump()["storages"]
    return storages["staticfiles"]["OPTIONS"]


def test_staticfiles_storage_uses_internal_endpoint_by_default() -> None:
    settings = DjangoStorageSettings(
        s3_settings=AWSS3Settings(
            endpoint_url="http://minio:9000",
            public_endpoint_url=None,
            access_key_id="access-key",
            secret_access_key=SecretStr("secret-key"),
            public_bucket_name="public-assets",
        ),
    )

    static_options = _get_static_options(settings)

    assert static_options["endpoint_url"] == "http://minio:9000"
    assert static_options["bucket_name"] == "public-assets"
    assert "custom_domain" not in static_options


def test_staticfiles_storage_uses_public_endpoint_for_generated_urls() -> None:
    settings = DjangoStorageSettings(
        s3_settings=AWSS3Settings(
            endpoint_url="http://minio:9000",
            public_endpoint_url="http://localhost:9000",
            access_key_id="access-key",
            secret_access_key=SecretStr("secret-key"),
        ),
    )

    static_options = _get_static_options(settings)

    assert static_options["endpoint_url"] == "http://minio:9000"
    assert static_options["custom_domain"] == "localhost:9000/public"
    assert static_options["url_protocol"] == "http:"
