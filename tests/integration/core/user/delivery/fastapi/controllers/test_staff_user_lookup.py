from http import HTTPStatus

from fastapi_template.core.user.entities.user import User
from tests.integration.factories import TestClientFactory, TestUserFactory

_PASSWORD_HASH = "hash"  # noqa: S105


def test_staff_user_lookup_allows_staff_user(
    test_client_factory: TestClientFactory,
    user_factory: TestUserFactory,
) -> None:
    staff_user = user_factory(username="staff_user", is_staff=True)
    other_user = user_factory(username="other_user")
    with test_client_factory(auth_for_user=staff_user) as test_client:
        response = test_client.get(f"/api/v1/users/{other_user.id}")

    assert response.status_code == HTTPStatus.OK


def test_staff_user_lookup_rejects_non_staff_user(
    test_client_factory: TestClientFactory,
    user_factory: TestUserFactory,
) -> None:
    non_staff_user = user_factory(username="non_staff_user", is_staff=False)
    other_user = user_factory(username="other_user")
    with test_client_factory(auth_for_user=non_staff_user) as test_client:
        response = test_client.get(f"/api/v1/users/{other_user.id}")

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_staff_user_lookup_rejects_missing_bearer_token(
    test_client_factory: TestClientFactory,
    user_factory: TestUserFactory,
) -> None:
    other_user = user_factory(username="other_user")
    with test_client_factory() as test_client:
        response = test_client.get(f"/api/v1/users/{other_user.id}")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.headers["www-authenticate"] == "Bearer"


def test_staff_user_lookup_rejects_missing_authenticated_user(
    test_client_factory: TestClientFactory,
    user_factory: TestUserFactory,
) -> None:
    other_user = user_factory(username="other_user")
    with test_client_factory(auth_for_user=_missing_user()) as test_client:
        response = test_client.get(f"/api/v1/users/{other_user.id}")

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
