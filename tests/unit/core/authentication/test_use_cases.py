from unittest.mock import MagicMock

import pytest

from fastdjango.core.authentication.dtos import IssueTokenDTO, TokenRequestContextDTO
from fastdjango.core.authentication.services.jwt import JWTService
from fastdjango.core.authentication.services.refresh_session import RefreshSessionService
from fastdjango.core.authentication.use_cases import TokenUseCase
from fastdjango.core.user.use_cases import UserUseCase

_INVALID_PASSWORD = "invalid-password"  # noqa: S105


def test_issue_token_rejects_invalid_credentials() -> None:
    user_use_case = MagicMock(spec=UserUseCase)
    user_use_case.get_user_by_username_and_password.return_value = None
    use_case = TokenUseCase(
        _jwt_service=MagicMock(spec=JWTService),
        _refresh_session_service=MagicMock(spec=RefreshSessionService),
        _user_use_case=user_use_case,
    )

    with pytest.raises(TokenUseCase.INVALID_CREDENTIALS_ERROR):
        use_case.issue_token(
            data=IssueTokenDTO(username="unknown", password=_INVALID_PASSWORD),
            context=TokenRequestContextDTO(user_agent="test", ip_address_trace=None),
        )
