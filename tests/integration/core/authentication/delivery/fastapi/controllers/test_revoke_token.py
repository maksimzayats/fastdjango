from http import HTTPStatus

import pytest

from fastapi_template.core.authentication.delivery.fastapi.schemas.token_response import (
    TokenResponseSchema,
)
from fastapi_template.core.user.entities.user import User
from tests.integration.factories import TestClientFactory, TestUserFactory

_TEST_PASSWORD = "test-password"  # noqa: S105
_REFRESH_TOKEN = "refresh-token"  # noqa: S105
_PASSWORD_HASH = "hash"  # noqa: S105


@pytest.fixture(scope="function")
def user(user_factory: TestUserFactory) -> User:
    return user_factory(username="test", password=_TEST_PASSWORD)


def test_revoke_token_prevents_later_refresh(
    test_client_factory: TestClientFactory,
    user: User,
) -> None:
    with test_client_factory() as test_client:
        response = test_client.post(
            "/api/v1/auth/token",
            json={"username": user.username, "password": _TEST_PASSWORD},
        )
        token_response = TokenResponseSchema.model_validate(response.json())

        response = test_client.post(
            "/api/v1/auth/token/refresh",
            json={"refresh_token": token_response.refresh_token},
        )
        token_response = TokenResponseSchema.model_validate(response.json())

        response = test_client.post(
            "/api/v1/auth/token/revoke",
            json={"refresh_token": token_response.refresh_token},
            headers={"Authorization": f"Bearer {token_response.access_token}"},
        )
        revoke_status = response.status_code

        response = test_client.post(
            "/api/v1/auth/token/refresh",
            json={"refresh_token": token_response.refresh_token},
        )

    assert revoke_status == HTTPStatus.OK
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_revoke_token_rejects_missing_bearer_token(
    test_client_factory: TestClientFactory,
) -> None:
    with test_client_factory() as test_client:
        response = test_client.post(
            "/api/v1/auth/token/revoke",
            json={"refresh_token": _REFRESH_TOKEN},
        )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["www-authenticate"] == "Bearer"


def test_revoke_token_rejects_missing_authenticated_user(
    test_client_factory: TestClientFactory,
) -> None:
    with test_client_factory(auth_for_user=_missing_user()) as test_client:
        response = test_client.post(
            "/api/v1/auth/token/revoke",
            json={"refresh_token": _REFRESH_TOKEN},
        )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["www-authenticate"] == "Bearer"


def _missing_user() -> User:
    return User(
        id=404,
        username="missing",
        email="missing@example.com",
        first_name="Missing",
        last_name="User",
        password_hash=_PASSWORD_HASH,
    )
