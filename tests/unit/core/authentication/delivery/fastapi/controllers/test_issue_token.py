from typing import cast

import pytest
from fastapi import HTTPException, Request

from fastapi_template.core.authentication.delivery.fastapi.controllers.issue_token import (
    IssueTokenController,
)
from fastapi_template.core.authentication.delivery.fastapi.schemas.issue_token_request import (
    IssueTokenRequestSchema,
)
from fastapi_template.core.authentication.dtos.issue_token import IssueTokenDTO
from fastapi_template.core.authentication.dtos.token import TokenDTO
from fastapi_template.core.authentication.exceptions.invalid_credentials import (
    InvalidCredentialsError,
)
from fastapi_template.core.authentication.use_cases.issue_token import IssueTokenUseCase
from fastapi_template.core.shared.delivery.fastapi.request import RequestInfoService

_TEST_PASSWORD = "secret"  # noqa: S105
_ACCESS_TOKEN = "access-token"  # noqa: S105
_REFRESH_TOKEN = "refresh-token"  # noqa: S105


class RecordingIssueTokenUseCase:
    data: IssueTokenDTO | None = None

    async def execute(self, *, data: IssueTokenDTO, context: object) -> TokenDTO:
        self.data = data
        return _token()


class StubRequestInfoService:
    def get_user_agent(self, *, request: Request) -> str:
        return "test-agent"

    def get_user_ip_trace(self, *, request: Request) -> str:
        return "127.0.0.1"


@pytest.mark.anyio
async def test_issue_token_controller_maps_issue_schema_to_dto() -> None:
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
async def test_issue_token_controller_translates_invalid_credentials() -> None:
    controller = _build_controller()

    with pytest.raises(HTTPException) as exc_info:
        await controller.handle_exception(InvalidCredentialsError())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid username or password"


@pytest.mark.anyio
async def test_issue_token_controller_reraises_unhandled_errors() -> None:
    controller = _build_controller()
    error = RuntimeError("unexpected")

    with pytest.raises(RuntimeError) as exc_info:
        await controller.handle_exception(error)

    assert exc_info.value is error


def _build_controller(
    *,
    request_info_service: RequestInfoService | None = None,
    issue_token_use_case: IssueTokenUseCase | None = None,
) -> IssueTokenController:
    return IssueTokenController(
        _request_info_service=request_info_service or cast(RequestInfoService, object()),
        _issue_token_use_case=issue_token_use_case or cast(IssueTokenUseCase, object()),
    )


def _request() -> Request:
    return Request({"type": "http", "headers": []})


def _token() -> TokenDTO:
    return TokenDTO(access_token=_ACCESS_TOKEN, refresh_token=_REFRESH_TOKEN)
