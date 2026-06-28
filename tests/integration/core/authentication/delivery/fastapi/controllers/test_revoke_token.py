from http import HTTPStatus
from typing import cast

import pytest
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth_factory import (
    JWTAuthFactory,
)
from fastapi_template.core.authentication.delivery.fastapi.controllers.revoke_token import (
    RevokeTokenController,
)
from fastapi_template.core.authentication.delivery.fastapi.schemas.token_response import (
    TokenResponseSchema,
)
from fastapi_template.core.authentication.delivery.fastapi.throttling.user_throttler_factory import (
    UserThrottlerFactory,
)
from fastapi_template.core.authentication.use_cases.revoke_token import RevokeTokenUseCase
from fastapi_template.core.shared.delivery.fastapi.throttling.ip_throttler_factory import (
    IPThrottlerFactory,
)
from fastapi_template.core.user.entities.user import User
from tests.integration.factories import TestClientFactory, TestUserFactory

_TEST_PASSWORD = "test-password"  # noqa: S105
_REFRESH_TOKEN = "refresh-token"  # noqa: S105


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


def test_revoke_token_applies_ip_throttle_before_jwt_auth() -> None:
    jwt_auth_factory = RecordingJWTAuthFactory()
    user_throttler_factory = RecordingUserThrottlerFactory()
    controller = RevokeTokenController(
        _jwt_auth_factory=cast(JWTAuthFactory, jwt_auth_factory),
        _ip_throttler_factory=cast(IPThrottlerFactory, RejectingIPThrottlerFactory()),
        _user_throttler_factory=cast(UserThrottlerFactory, user_throttler_factory),
        _revoke_token_use_case=cast(RevokeTokenUseCase, object()),
    )
    app = FastAPI()
    router = APIRouter()
    controller.register(router)
    app.include_router(router)

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/auth/token/revoke",
            json={"refresh_token": _REFRESH_TOKEN},
        )

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert jwt_auth_factory.dependency_called is False
    assert user_throttler_factory.dependency_called is False


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


class RecordingJWTAuthFactory:
    dependency_called = False

    def __call__(self) -> object:
        return self.authenticate

    async def authenticate(self, request: Request) -> None:
        self.dependency_called = True
        msg = "JWT auth should not run before IP throttling."
        raise AssertionError(msg)


class RejectingIPThrottlerFactory:
    def __call__(self, *, quota: object) -> object:
        return self.throttle

    async def throttle(self, request: Request) -> None:
        raise HTTPException(
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            detail="Too many requests",
        )


class RecordingUserThrottlerFactory:
    dependency_called = False

    def __call__(self, *, quota: object) -> object:
        return self.throttle

    async def throttle(self, request: Request) -> None:
        self.dependency_called = True
