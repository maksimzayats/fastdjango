from http import HTTPStatus

import pytest

from fastapi_template.core.authentication.delivery.fastapi.schemas.token_response import (
    TokenResponseSchema,
)
from fastapi_template.core.user.delivery.fastapi.schemas.user import UserSchema
from fastapi_template.core.user.entities.user import User
from tests.integration.factories import TestClientFactory, TestUserFactory

_TEST_PASSWORD = "test-password"  # noqa: S105


@pytest.fixture(scope="function")
def user(user_factory: TestUserFactory) -> User:
    return user_factory(username="test", password=_TEST_PASSWORD)


def test_issue_token_returns_jwt_tokens(
    test_client_factory: TestClientFactory,
    user: User,
) -> None:
    with test_client_factory() as test_client:
        response = test_client.post(
            "/api/v1/auth/token",
            json={"username": user.username, "password": _TEST_PASSWORD},
        )
        token_data = response.json()
        token_response = TokenResponseSchema.model_validate(token_data)

        response = test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token_response.access_token}"},
        )
        user_data = UserSchema.model_validate(response.json())

    assert response.status_code == HTTPStatus.OK
    assert set(token_data) == {"access_token", "refresh_token"}
    assert user_data.id == user.id
    assert user_data.username == user.username
    assert user_data.email == user.email


def test_issue_token_rejects_invalid_password(
    test_client_factory: TestClientFactory,
    user: User,
) -> None:
    with test_client_factory() as test_client:
        response = test_client.post(
            "/api/v1/auth/token",
            json={"username": user.username, "password": "invalid-password"},
        )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
