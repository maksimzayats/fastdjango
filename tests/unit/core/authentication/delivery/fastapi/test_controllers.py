from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException, Request

from fastapi_template.core.authentication.delivery.fastapi.auth import (
    AuthenticatedRequest,
    JWTAuthFactory,
)
from fastapi_template.core.authentication.delivery.fastapi.controllers import (
    AuthenticationTokenController,
)
from fastapi_template.core.authentication.delivery.fastapi.schemas import (
    IssueTokenRequestSchema,
    RefreshTokenRequestSchema,
)
from fastapi_template.core.authentication.delivery.fastapi.throttling import UserThrottlerFactory
from fastapi_template.core.authentication.dtos import IssueTokenDTO, RefreshTokenDTO, TokenDTO
from fastapi_template.core.authentication.exceptions import (
    InvalidCredentialsError,
    RefreshTokenError,
)
from fastapi_template.core.authentication.use_cases import (
    IssueTokenUseCase,
    RefreshTokenUseCase,
    RevokeTokenUseCase,
)
from fastapi_template.core.shared.delivery.fastapi.request import RequestInfoService
from fastapi_template.core.shared.delivery.fastapi.throttling import IPThrottlerFactory
from fastapi_template.core.user.entities import User

_TEST_PASSWORD = "secret"  # noqa: S105
_ACCESS_TOKEN = "access-token"  # noqa: S105
_REFRESH_TOKEN = "refresh-token"  # noqa: S105
_PASSWORD_HASH = "hash"  # noqa: S105


class RecordingIssueTokenUseCase:
    data: IssueTokenDTO | None = None

    async def execute(self, *, data: IssueTokenDTO, context: object) -> TokenDTO:
        self.data = data
        return _token()


class RecordingRefreshTokenUseCase:
    data: RefreshTokenDTO | None = None

    async def execute(self, *, data: RefreshTokenDTO) -> TokenDTO:
        self.data = data
        return _token()


class RecordingRevokeTokenUseCase:
    data: RefreshTokenDTO | None = None

    async def execute(self, *, data: RefreshTokenDTO, user: User) -> None:
        self.data = data


class StubRequestInfoService:
    def get_user_agent(self, *, request: Request) -> str:
        return "test-agent"

    def get_user_ip_trace(self, *, request: Request) -> str:
        return "127.0.0.1"


@pytest.mark.anyio
async def test_authentication_controller_maps_issue_schema_to_dto() -> None:
    issue_token_use_case = RecordingIssueTokenUseCase()
    controller = _build_controller(
        issue_token_use_case=cast(IssueTokenUseCase, issue_token_use_case),
        request_info_service=cast(RequestInfoService, StubRequestInfoService()),
    )

    response = await controller.issue_token(
        request=_request(),
        body=IssueTokenRequestSchema(username="test", password=_TEST_PASSWORD),
    )

    assert issue_token_use_case.data == IssueTokenDTO(username="test", password=_TEST_PASSWORD)
    assert response.access_token == _ACCESS_TOKEN


@pytest.mark.anyio
async def test_authentication_controller_maps_refresh_schema_to_dto() -> None:
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
async def test_authentication_controller_maps_revoke_schema_to_dto() -> None:
    revoke_token_use_case = RecordingRevokeTokenUseCase()
    controller = _build_controller(
        revoke_token_use_case=cast(RevokeTokenUseCase, revoke_token_use_case),
    )

    await controller.revoke_token(
        request=cast(AuthenticatedRequest, SimpleNamespace(state=SimpleNamespace(user=_user()))),
        body=RefreshTokenRequestSchema(refresh_token=_REFRESH_TOKEN),
    )

    assert revoke_token_use_case.data == RefreshTokenDTO(refresh_token=_REFRESH_TOKEN)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("exception", "detail"),
    [
        (InvalidCredentialsError(), "Invalid username or password"),
        (RefreshTokenUseCase.INVALID_REFRESH_TOKEN_ERROR(), "Invalid refresh token"),
        (RevokeTokenUseCase.EXPIRED_REFRESH_TOKEN_ERROR(), "Refresh token expired or revoked"),
        (RefreshTokenError(), "Refresh token error"),
    ],
)
async def test_authentication_controller_translates_domain_errors(
    exception: Exception,
    detail: str,
) -> None:
    controller = _build_controller()

    with pytest.raises(HTTPException) as exc_info:
        await controller.handle_exception(exception)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == detail


@pytest.mark.anyio
async def test_authentication_controller_reraises_unhandled_errors() -> None:
    controller = _build_controller()
    error = RuntimeError("unexpected")

    with pytest.raises(RuntimeError) as exc_info:
        await controller.handle_exception(error)

    assert exc_info.value is error


def _build_controller(
    *,
    request_info_service: RequestInfoService | None = None,
    issue_token_use_case: IssueTokenUseCase | None = None,
    refresh_token_use_case: RefreshTokenUseCase | None = None,
    revoke_token_use_case: RevokeTokenUseCase | None = None,
) -> AuthenticationTokenController:
    return AuthenticationTokenController(
        _jwt_auth_factory=cast(JWTAuthFactory, lambda **_kwargs: object()),
        _request_info_service=request_info_service or cast(RequestInfoService, object()),
        _ip_throttler_factory=cast(IPThrottlerFactory, object()),
        _user_throttler_factory=cast(UserThrottlerFactory, object()),
        _issue_token_use_case=issue_token_use_case or cast(IssueTokenUseCase, object()),
        _refresh_token_use_case=refresh_token_use_case or cast(RefreshTokenUseCase, object()),
        _revoke_token_use_case=revoke_token_use_case or cast(RevokeTokenUseCase, object()),
    )


def _request() -> Request:
    return Request({"type": "http", "headers": []})


def _token() -> TokenDTO:
    return TokenDTO(access_token=_ACCESS_TOKEN, refresh_token=_REFRESH_TOKEN)


def _user() -> User:
    return User(
        id=1,
        username="test",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=_PASSWORD_HASH,
    )
