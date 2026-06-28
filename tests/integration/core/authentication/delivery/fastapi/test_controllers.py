from http import HTTPStatus

import pytest

from fastapi_template.core.authentication.delivery.fastapi.schemas import TokenResponseSchema
from fastapi_template.core.user.delivery.fastapi.schemas import UserSchema
from fastapi_template.core.user.entities import User
from tests.integration.factories import TestClientFactory, TestUserFactory

_TEST_PASSWORD = "test-password"  # noqa: S105


@pytest.fixture(scope="function")
def user(user_factory: TestUserFactory) -> User:
    return user_factory(username="test", password=_TEST_PASSWORD)


class TestAuthenticationTokenController:
    """Tests for AuthenticationTokenController endpoints."""

    def test_jwt_token_generation(
        self,
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

    def test_jwt_token_generation_for_invalid_password(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        with test_client_factory() as test_client:
            response = test_client.post(
                "/api/v1/auth/token",
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
                "/api/v1/auth/token",
                json={"username": user.username, "password": _TEST_PASSWORD},
            )
            token_response = TokenResponseSchema.model_validate(response.json())

            response = test_client.post(
                "/api/v1/auth/token/refresh",
                json={"refresh_token": token_response.refresh_token},
            )
            token_data = response.json()
            token_response = TokenResponseSchema.model_validate(token_data)

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
        assert set(token_data) == {"access_token", "refresh_token"}
        assert response.status_code == HTTPStatus.UNAUTHORIZED
