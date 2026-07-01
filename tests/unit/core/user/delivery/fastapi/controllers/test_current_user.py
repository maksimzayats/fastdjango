from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request import (
    AuthenticatedRequest,
)
from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth_factory import (
    JWTAuthFactory,
)
from fastapi_template.core.user.delivery.fastapi.controllers.current_user import (
    CurrentUserController,
)
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.use_cases.get_active_user_by_id import (
    GetActiveUserByIdUseCase,
)

_PASSWORD_HASH = "hash"  # noqa: S105


class FakeGetActiveUserByIdUseCase:
    def __init__(self, *, user: User | None) -> None:
        self._user = user
        self.user_id: int | None = None

    async def execute(self, *, user_id: int) -> User | None:
        self.user_id = user_id
        return self._user


@pytest.mark.anyio
async def test_current_user_controller_returns_loaded_user() -> None:
    user = _build_user(user_id=1)
    use_case = FakeGetActiveUserByIdUseCase(user=user)
    controller = _build_controller(
        get_active_user_by_id_use_case=cast(GetActiveUserByIdUseCase, use_case),
    )

    result = await controller.get_current_user(
        request=cast(AuthenticatedRequest, SimpleNamespace(state=SimpleNamespace(user_id=1))),
    )

    assert result.id == user.id
    assert use_case.user_id == user.id


@pytest.mark.anyio
async def test_current_user_controller_rejects_missing_user() -> None:
    controller = _build_controller(
        get_active_user_by_id_use_case=cast(
            GetActiveUserByIdUseCase,
            FakeGetActiveUserByIdUseCase(user=None),
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await controller.get_current_user(
            request=cast(AuthenticatedRequest, SimpleNamespace(state=SimpleNamespace(user_id=1))),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "User not found"
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def _build_controller(
    *,
    get_active_user_by_id_use_case: GetActiveUserByIdUseCase,
) -> CurrentUserController:
    return CurrentUserController(
        _jwt_auth_factory=cast(JWTAuthFactory, object),
        _get_active_user_by_id_use_case=get_active_user_by_id_use_case,
    )


def _build_user(*, user_id: int) -> User:
    return User(
        id=user_id,
        username="test_user",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=_PASSWORD_HASH,
    )
