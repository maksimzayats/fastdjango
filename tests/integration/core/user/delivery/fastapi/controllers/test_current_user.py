from http import HTTPStatus

import pytest

from fastapi_template.core.user.entities.user import User
from tests.integration.factories import TestClientFactory, TestUserFactory

_TEST_PASSWORD = "test-password"  # noqa: S105


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
