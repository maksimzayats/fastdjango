from http import HTTPStatus

import pytest

from fastapi_template.core.user.constants import PASSWORD_MAX_LENGTH, USER_NAME_MAX_LENGTH
from fastapi_template.core.user.delivery.fastapi.schemas import UserSchema
from fastapi_template.core.user.entities import User
from tests.integration.factories import TestClientFactory, TestUserFactory

_TEST_PASSWORD = "test-password"  # noqa: S105


@pytest.fixture(scope="function")
def user(user_factory: TestUserFactory) -> User:
    return user_factory(username="test", password=_TEST_PASSWORD)


class TestUserController:
    """Tests for UserController endpoints."""

    def test_create_user(self, test_client_factory: TestClientFactory) -> None:
        with test_client_factory() as test_client:
            response = test_client.post(
                "/api/v1/users/",
                json={
                    "username": "test_new_user",
                    "email": "new_user@test.com",
                    "password": _TEST_PASSWORD,
                    "first_name": "Test",
                    "last_name": "User",
                },
            )

        response_data = UserSchema.model_validate(response.json())
        assert response.status_code == HTTPStatus.OK
        assert set(response.json()) == {
            "email",
            "first_name",
            "id",
            "is_staff",
            "is_superuser",
            "last_name",
            "username",
        }
        assert response_data.username == "test_new_user"

    @pytest.mark.parametrize(
        ("field_name", "field_value"),
        [
            ("password", "x" * (PASSWORD_MAX_LENGTH + 1)),
            ("username", "x" * (USER_NAME_MAX_LENGTH + 1)),
        ],
    )
    def test_create_user_rejects_overlong_fields(
        self,
        test_client_factory: TestClientFactory,
        field_name: str,
        field_value: str,
    ) -> None:
        payload = {
            "username": "test_new_user",
            "email": "new_user@test.com",
            "password": _TEST_PASSWORD,
            "first_name": "Test",
            "last_name": "User",
        }
        payload[field_name] = field_value

        with test_client_factory() as test_client:
            response = test_client.post(
                "/api/v1/users/",
                json=payload,
            )

        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_auth_for_user(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        with test_client_factory(auth_for_user=user) as test_client:
            response = test_client.get("/api/v1/users/me")

        assert response.status_code == HTTPStatus.OK

    def test_staff_auth_for_user(
        self,
        test_client_factory: TestClientFactory,
        user_factory: TestUserFactory,
    ) -> None:
        staff_user = user_factory(username="staff_user", is_staff=True)
        other_user = user_factory(username="other_user")
        with test_client_factory(auth_for_user=staff_user) as test_client:
            response = test_client.get(f"/api/v1/users/{other_user.id}")

        assert response.status_code == HTTPStatus.OK

    def test_non_staff_auth_for_user(
        self,
        test_client_factory: TestClientFactory,
        user_factory: TestUserFactory,
    ) -> None:
        non_staff_user = user_factory(username="non_staff_user", is_staff=False)
        other_user = user_factory(username="other_user")
        with test_client_factory(auth_for_user=non_staff_user) as test_client:
            response = test_client.get(f"/api/v1/users/{other_user.id}")

        assert response.status_code == HTTPStatus.FORBIDDEN
