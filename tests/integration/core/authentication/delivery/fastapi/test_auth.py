from http import HTTPStatus

import pytest
from throttled.asyncio import MemoryStore

from fastdjango.core.user.delivery.fastapi.schemas import UserSchema
from fastdjango.infrastructure.throttled.throttler import AsyncThrottlerStoreFactory
from fastdjango.ioc.container import get_container
from tests.integration.factories import TestClientFactory


@pytest.mark.django_db(transaction=True)
def test_static_api_key_mode_authenticates_current_user_and_skips_token_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTHENTICATION_MODE", "static-api-keys")
    monkeypatch.setenv(
        "STATIC_API_KEYS",
        (
            '{"test-static-key":{"id":42,"username":"service","email":"service@example.com",'
            '"first_name":"Service","last_name":"Account","is_staff":true,'
            '"is_superuser":false}}'
        ),
    )
    container = get_container()
    container.add_instance(lambda: MemoryStore(), provides=AsyncThrottlerStoreFactory)  # noqa: PLW0108
    test_client_factory = TestClientFactory(container=container)

    with test_client_factory(headers={"X-API-Key": "test-static-key"}) as test_client:
        user_response = test_client.get("/v1/users/me")
        token_response = test_client.post(
            "/v1/auth/token",
            json={"username": "service", "password": "unused"},
        )

    user_data = UserSchema.model_validate(user_response.json())
    assert user_response.status_code == HTTPStatus.OK
    assert user_data.id == 42
    assert user_data.username == "service"
    assert user_data.email == "service@example.com"
    assert token_response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db(transaction=True)
def test_custom_authentication_mode_skips_built_in_protected_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTHENTICATION_MODE", "custom")
    container = get_container()
    container.add_instance(lambda: MemoryStore(), provides=AsyncThrottlerStoreFactory)  # noqa: PLW0108
    test_client_factory = TestClientFactory(container=container)

    with test_client_factory() as test_client:
        user_response = test_client.get("/v1/users/me")
        token_response = test_client.post(
            "/v1/auth/token",
            json={"username": "service", "password": "unused"},
        )

    assert user_response.status_code == HTTPStatus.NOT_FOUND
    assert token_response.status_code == HTTPStatus.NOT_FOUND
