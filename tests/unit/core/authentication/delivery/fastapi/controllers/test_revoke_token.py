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
from fastapi_template.core.authentication.delivery.fastapi.controllers.revoke_token import (
    RevokeTokenController,
)
from fastapi_template.core.authentication.delivery.fastapi.schemas.revoke_token_request import (
    RevokeTokenRequestSchema,
)
from fastapi_template.core.authentication.delivery.fastapi.throttling.user_throttler_factory import (
    UserThrottlerFactory,
)
from fastapi_template.core.authentication.dtos.refresh_token import RefreshTokenDTO
from fastapi_template.core.authentication.exceptions.refresh_token import RefreshTokenError
from fastapi_template.core.authentication.use_cases.revoke_token import RevokeTokenUseCase

_REFRESH_TOKEN = "refresh-token"  # noqa: S105


class RecordingRevokeTokenUseCase:
    data: RefreshTokenDTO | None = None
    user_id: int | None = None

    async def execute(self, *, data: RefreshTokenDTO, user_id: int) -> None:
        self.data = data
        self.user_id = user_id


@pytest.mark.anyio
async def test_revoke_token_controller_maps_revoke_schema_to_dto() -> None:
    revoke_token_use_case = RecordingRevokeTokenUseCase()
    controller = _build_controller(
        revoke_token_use_case=cast(RevokeTokenUseCase, revoke_token_use_case),
    )

    await controller.revoke_token(
        request=cast(AuthenticatedRequest, SimpleNamespace(state=SimpleNamespace(user_id=1))),
        body=RevokeTokenRequestSchema(refresh_token=_REFRESH_TOKEN),
    )

    assert revoke_token_use_case.data == RefreshTokenDTO(refresh_token=_REFRESH_TOKEN)
    assert revoke_token_use_case.user_id == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("exception", "detail"),
    [
        (RevokeTokenUseCase.INVALID_REFRESH_TOKEN_ERROR(), "Invalid refresh token"),
        (RevokeTokenUseCase.EXPIRED_REFRESH_TOKEN_ERROR(), "Refresh token expired or revoked"),
        (RefreshTokenError(), "Refresh token error"),
        (RevokeTokenUseCase.AUTHENTICATED_USER_NOT_FOUND_ERROR(), "User not found"),
    ],
)
async def test_revoke_token_controller_translates_domain_errors(
    exception: Exception,
    detail: str,
) -> None:
    controller = _build_controller()

    with pytest.raises(HTTPException) as exc_info:
        await controller.handle_exception(exception)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == detail
    if detail == "User not found":
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.anyio
async def test_revoke_token_controller_reraises_unhandled_errors() -> None:
    controller = _build_controller()
    error = RuntimeError("unexpected")

    with pytest.raises(RuntimeError) as exc_info:
        await controller.handle_exception(error)

    assert exc_info.value is error


def _build_controller(
    *,
    revoke_token_use_case: RevokeTokenUseCase | None = None,
) -> RevokeTokenController:
    return RevokeTokenController(
        _jwt_auth_factory=cast(JWTAuthFactory, object),
        _user_throttler_factory=cast(UserThrottlerFactory, object()),
        _revoke_token_use_case=revoke_token_use_case or cast(RevokeTokenUseCase, object()),
    )
