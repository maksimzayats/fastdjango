from http import HTTPStatus

import pytest

from fastapi_template.core.user.entities.user import User
from tests.integration.factories import TestClientFactory, TestUserFactory

_TEST_PASSWORD = "test-password"  # noqa: S105
_PASSWORD_HASH = "hash"  # noqa: S105


@pytest.fixture(scope="function")
def user(user_factory: TestUserFactory) -> User:
    return user_factory(username="test", password=_TEST_PASSWORD)


def test_current_user_returns_authenticated_user(
    test_client_factory: TestClientFactory,
    user: User,
) -> None:
    with test_client_factory(auth_for_user=user) as test_client:
        response = test_client.get("/api/v1/users/me")

    assert response.status_code == HTTPStatus.OK


def test_current_user_rejects_missing_bearer_token(
    test_client_factory: TestClientFactory,
) -> None:
    with test_client_factory() as test_client:
        response = test_client.get("/api/v1/users/me")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["www-authenticate"] == "Bearer"


def test_current_user_rejects_missing_authenticated_user(
    test_client_factory: TestClientFactory,
) -> None:
    with test_client_factory(auth_for_user=_missing_user()) as test_client:
        response = test_client.get("/api/v1/users/me")

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
