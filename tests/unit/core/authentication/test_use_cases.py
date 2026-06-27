from unittest.mock import AsyncMock, MagicMock

import pytest

from modern_python_template.core.authentication.dtos import IssueTokenDTO, TokenRequestContextDTO
from modern_python_template.core.authentication.services.jwt import JWTService
from modern_python_template.core.authentication.services.refresh_session import (
    RefreshSessionService,
)
from modern_python_template.core.authentication.use_cases import TokenUseCase
from modern_python_template.core.user.use_cases import UserUseCase

_INVALID_PASSWORD = "invalid-password"  # noqa: S105


@pytest.mark.anyio
async def test_issue_token_rejects_invalid_credentials() -> None:
    user_use_case = MagicMock(spec=UserUseCase)
    user_use_case.get_user_by_username_and_password = AsyncMock(return_value=None)
    use_case = TokenUseCase(
        _jwt_service=MagicMock(spec=JWTService),
        _refresh_session_service=MagicMock(spec=RefreshSessionService),
        _user_use_case=user_use_case,
    )

    with pytest.raises(TokenUseCase.INVALID_CREDENTIALS_ERROR):
        await use_case.issue_token(
            data=IssueTokenDTO(username="unknown", password=_INVALID_PASSWORD),
            context=TokenRequestContextDTO(user_agent="test", ip_address_trace=None),
        )
