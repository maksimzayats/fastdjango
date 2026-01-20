from http import HTTPStatus

import pytest

from core.user.models import User
from delivery.http.controllers.user.schemas import TokenResponseSchema, UserSchema
from tests.integration.factories import TestClientFactory, TestUserFactory

_TEST_PASSWORD = "test-password"  # noqa: S105


@pytest.fixture(scope="function")
def user(user_factory: TestUserFactory) -> User:
    return user_factory(username="test", password=_TEST_PASSWORD)


@pytest.mark.django_db(transaction=True)
class TestUserController:
    """Tests for UserController endpoints."""

    def test_create_user(self, test_client_factory: TestClientFactory) -> None:
        with test_client_factory() as test_client:
            response = test_client.post(
                "/v1/users/",
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
        assert response_data.username == "test_new_user"

    def test_jwt_token_generation(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        with test_client_factory() as test_client:
            response = test_client.post(
                "/v1/users/me/token",
                json={"username": user.username, "password": _TEST_PASSWORD},
            )
            token_response = TokenResponseSchema.model_validate(response.json())

            response = test_client.get(
                "/v1/users/me",
                headers={"Authorization": f"Bearer {token_response.access_token}"},
            )
            user_data = UserSchema.model_validate(response.json())

        assert response.status_code == HTTPStatus.OK
        assert user_data.id == user.pk
        assert user_data.username == user.username
        assert user_data.email == user.email

    def test_jwt_token_generation_for_invalid_password(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        with test_client_factory() as test_client:
            response = test_client.post(
                "/v1/users/me/token",
                json={"username": user.username, "password": "invalid-password"},
            )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_jwt_token_refresh_revoke_flow(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        with test_client_factory() as test_client:
            response = test_client.post(
                "/v1/users/me/token",
                json={"username": user.username, "password": _TEST_PASSWORD},
            )
            token_response = TokenResponseSchema.model_validate(response.json())

            response = test_client.post(
                "/v1/users/me/token/refresh",
                json={"refresh_token": token_response.refresh_token},
            )
            token_response = TokenResponseSchema.model_validate(response.json())

            response = test_client.post(
                "/v1/users/me/token/revoke",
                json={"refresh_token": token_response.refresh_token},
                headers={"Authorization": f"Bearer {token_response.access_token}"},
            )
            revoke_status = response.status_code

            response = test_client.post(
                "/v1/users/me/token/refresh",
                json={"refresh_token": token_response.refresh_token},
            )

        assert revoke_status == HTTPStatus.OK
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_auth_for_user(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        with test_client_factory(auth_for_user=user) as test_client:
            response = test_client.get("/v1/users/me")

        assert response.status_code == HTTPStatus.OK

    def test_staff_auth_for_user(
        self,
        test_client_factory: TestClientFactory,
        user_factory: TestUserFactory,
    ) -> None:
        staff_user = user_factory(username="staff_user", is_staff=True)
        other_user = user_factory(username="other_user")
        with test_client_factory(auth_for_user=staff_user) as test_client:
            response = test_client.get(f"/v1/users/{other_user.pk}")

        assert response.status_code == HTTPStatus.OK

    def test_non_staff_auth_for_user(
        self,
        test_client_factory: TestClientFactory,
        user_factory: TestUserFactory,
    ) -> None:
        non_staff_user = user_factory(username="non_staff_user", is_staff=False)
        other_user = user_factory(username="other_user")
        with test_client_factory(auth_for_user=non_staff_user) as test_client:
            response = test_client.get(f"/v1/users/{other_user.pk}")

        assert response.status_code == HTTPStatus.FORBIDDEN
