from typing import cast

import pytest
from fastapi import HTTPException

from fastapi_template.core.authentication.delivery.fastapi.controllers.refresh_token import (
    RefreshTokenController,
)
from fastapi_template.core.authentication.delivery.fastapi.schemas.refresh_token_request import (
    RefreshTokenRequestSchema,
)
from fastapi_template.core.authentication.dtos.refresh_token import RefreshTokenDTO
from fastapi_template.core.authentication.dtos.token import TokenDTO
from fastapi_template.core.authentication.exceptions.refresh_token import RefreshTokenError
from fastapi_template.core.authentication.use_cases.refresh_token import RefreshTokenUseCase

_ACCESS_TOKEN = "access-token"  # noqa: S105
_REFRESH_TOKEN = "refresh-token"  # noqa: S105


class RecordingRefreshTokenUseCase:
    data: RefreshTokenDTO | None = None

    async def execute(self, *, data: RefreshTokenDTO) -> TokenDTO:
        self.data = data
        return _token()


@pytest.mark.anyio
async def test_refresh_token_controller_maps_refresh_schema_to_dto() -> None:
    refresh_token_use_case = RecordingRefreshTokenUseCase()
    controller = _build_controller(
        refresh_token_use_case=cast(RefreshTokenUseCase, refresh_token_use_case),
    )

    response = await controller.refresh_token(
        body=RefreshTokenRequestSchema(refresh_token=_REFRESH_TOKEN),
    )

    assert refresh_token_use_case.data == RefreshTokenDTO(refresh_token=_REFRESH_TOKEN)
    assert response.refresh_token == _REFRESH_TOKEN


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("exception", "detail"),
    [
        (RefreshTokenUseCase.INVALID_REFRESH_TOKEN_ERROR(), "Invalid refresh token"),
        (RefreshTokenUseCase.EXPIRED_REFRESH_TOKEN_ERROR(), "Refresh token expired or revoked"),
        (RefreshTokenError(), "Refresh token error"),
    ],
)
async def test_refresh_token_controller_translates_domain_errors(
    exception: Exception,
    detail: str,
) -> None:
    controller = _build_controller()

    with pytest.raises(HTTPException) as exc_info:
        await controller.handle_exception(exception)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == detail


@pytest.mark.anyio
async def test_refresh_token_controller_reraises_unhandled_errors() -> None:
    controller = _build_controller()
    error = RuntimeError("unexpected")

    with pytest.raises(RuntimeError) as exc_info:
        await controller.handle_exception(error)

    assert exc_info.value is error


def _build_controller(
    *,
    refresh_token_use_case: RefreshTokenUseCase | None = None,
) -> RefreshTokenController:
    return RefreshTokenController(
        _refresh_token_use_case=refresh_token_use_case or cast(RefreshTokenUseCase, object()),
    )


def _token() -> TokenDTO:
    return TokenDTO(access_token=_ACCESS_TOKEN, refresh_token=_REFRESH_TOKEN)
