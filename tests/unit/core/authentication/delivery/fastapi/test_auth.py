from http import HTTPStatus

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.types import Scope

from fastdjango.core.authentication.delivery.fastapi.auth import (
    StaticAPIKeyAuth,
    StaticAPIKeyPrincipal,
    StaticAPIKeyRegistrySettings,
)


def test_static_api_key_registry_parses_json_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "STATIC_API_KEYS",
        (
            '{"env-key":{"id":7,"username":"service","email":"service@example.com",'
            '"is_staff":true,"is_superuser":false}}'
        ),
    )

    settings = StaticAPIKeyRegistrySettings()

    principal = settings.get_principal_for_api_key(api_key="env-key")
    assert principal is not None
    assert principal.pk == 7
    assert principal.username == "service"
    assert principal.is_staff is True


@pytest.mark.anyio
async def test_static_api_key_auth_sets_request_user() -> None:
    settings = _settings(is_staff=True)
    request = _request(headers={"X-API-Key": "valid-key"})
    auth = StaticAPIKeyAuth(settings=settings)

    api_key = await auth(request)

    assert api_key == "valid-key"
    assert request.state.user.username == "service"
    assert request.state.user.pk == 1


@pytest.mark.anyio
async def test_static_api_key_auth_rejects_missing_key() -> None:
    auth = StaticAPIKeyAuth(settings=_settings())

    with pytest.raises(HTTPException) as error:
        await auth(_request())

    assert error.value.status_code == HTTPStatus.UNAUTHORIZED
    assert error.value.detail == "API key is required"


@pytest.mark.anyio
async def test_static_api_key_auth_rejects_invalid_key() -> None:
    auth = StaticAPIKeyAuth(settings=_settings())

    with pytest.raises(HTTPException) as error:
        await auth(_request(headers={"X-API-Key": "invalid-key"}))

    assert error.value.status_code == HTTPStatus.UNAUTHORIZED
    assert error.value.detail == "Invalid API key"


@pytest.mark.anyio
async def test_static_api_key_auth_checks_staff_permission() -> None:
    auth = StaticAPIKeyAuth(settings=_settings(is_staff=False), require_staff=True)

    with pytest.raises(HTTPException) as error:
        await auth(_request(headers={"X-API-Key": "valid-key"}))

    assert error.value.status_code == HTTPStatus.FORBIDDEN
    assert error.value.detail == "Staff access required"


def _settings(*, is_staff: bool = False) -> StaticAPIKeyRegistrySettings:
    return StaticAPIKeyRegistrySettings(
        api_keys={
            "valid-key": StaticAPIKeyPrincipal(
                id=1,
                username="service",
                email="service@example.com",
                is_staff=is_staff,
                is_superuser=False,
            ),
        },
    )


def _request(*, headers: dict[str, str] | None = None) -> Request:
    header_items = [
        (key.lower().encode(), value.encode()) for key, value in (headers or {}).items()
    ]
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": header_items,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)
