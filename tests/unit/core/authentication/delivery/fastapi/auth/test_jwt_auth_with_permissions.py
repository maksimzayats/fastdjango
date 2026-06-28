from typing import Any, cast

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.types import Scope

from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth_with_permissions import (
    JWTAuthWithPermissions,
)
from fastapi_template.core.authentication.services.jwt import JWTService
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.services.permission import UserPermissionService
from fastapi_template.core.user.use_cases.get_active_user_by_id import (
    GetActiveUserByIdUseCase,
)


class FakeJWTService:
    EXPIRED_SIGNATURE_ERROR = JWTService.EXPIRED_SIGNATURE_ERROR
    INVALID_TOKEN_ERROR = JWTService.INVALID_TOKEN_ERROR

    def __init__(self, *, payload: dict[str, Any]) -> None:
        self._payload = payload

    def decode_token(self, *, token: str) -> dict[str, Any]:
        return self._payload


class FakeGetActiveUserByIdUseCase:
    def __init__(self, *, user: User | None) -> None:
        self._user = user

    async def execute(self, *, user_id: int) -> User | None:
        return self._user


@pytest.mark.anyio
async def test_jwt_auth_rejects_missing_staff_permission() -> None:
    auth = _build_permission_auth(require_staff=True, user=_build_user(is_staff=False))

    with pytest.raises(HTTPException) as exc_info:
        await auth(_request(token=_bearer_token()))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Permission denied"


@pytest.mark.anyio
async def test_jwt_auth_rejects_missing_superuser_permission() -> None:
    auth = _build_permission_auth(require_superuser=True, user=_build_user(is_superuser=False))

    with pytest.raises(HTTPException) as exc_info:
        await auth(_request(token=_bearer_token()))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Permission denied"


def _build_permission_auth(
    *,
    user: User,
    require_staff: bool = False,
    require_superuser: bool = False,
) -> JWTAuthWithPermissions:
    return JWTAuthWithPermissions(
        jwt_service=cast(JWTService, FakeJWTService(payload={"sub": str(user.id)})),
        get_active_user_by_id_use_case=cast(
            GetActiveUserByIdUseCase,
            FakeGetActiveUserByIdUseCase(user=user),
        ),
        user_permission_service=UserPermissionService(),
        require_staff=require_staff,
        require_superuser=require_superuser,
    )


def _request(*, token: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode()))

    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/users/me",
        "raw_path": b"/api/v1/users/me",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


def _build_user(
    *,
    is_staff: bool = True,
    is_superuser: bool = True,
) -> User:
    return User(
        id=1,
        username="test_user",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=_password_hash(),
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


def _bearer_token() -> str:
    return "signed-jwt-value"


def _password_hash() -> str:
    return "argon2-hash-value"
