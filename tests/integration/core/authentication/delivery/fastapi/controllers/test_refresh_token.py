from http import HTTPStatus

import pytest

from fastapi_template.core.authentication.delivery.fastapi.schemas.token_response import (
    TokenResponseSchema,
)
from fastapi_template.core.user.entities.user import User
from tests.integration.factories import (
    TestClientFactory,
    TestRefreshSessionFactory,
    TestUserFactory,
)

_TEST_PASSWORD = "test-password"  # noqa: S105


@pytest.fixture(scope="function")
def user(user_factory: TestUserFactory) -> User:
    return user_factory(username="test", password=_TEST_PASSWORD)


def test_refresh_token_rotates_refresh_session(
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
        token_data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert set(token_data) == {"access_token", "refresh_token"}
    assert token_data["refresh_token"] != token_response.refresh_token


def test_refresh_token_rejects_inactive_session_user(
    test_client_factory: TestClientFactory,
    user_factory: TestUserFactory,
    refresh_session_factory: TestRefreshSessionFactory,
) -> None:
    inactive_user = user_factory(
        username="inactive_user",
        password=_TEST_PASSWORD,
        is_active=False,
    )
    refresh_token = refresh_session_factory(user=inactive_user)

    with test_client_factory() as test_client:
        response = test_client.post(
            "/api/v1/auth/token/refresh",
            json={"refresh_token": refresh_token},
        )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
