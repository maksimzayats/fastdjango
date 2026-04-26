import pytest
from pydantic import SecretStr

from fastdjango.core.authentication.services.jwt import JWTService, JWTServiceSettings

_SECRET_KEY = "test-secret-key-with-enough-bytes"  # noqa: S105
_INVALID_TOKEN = "not-a-jwt"  # noqa: S105


def test_jwt_service_issues_decodable_access_token() -> None:
    service = JWTService(
        _settings=JWTServiceSettings(
            secret_key=SecretStr(_SECRET_KEY),
            typ="test+jwt",
        ),
    )

    token = service.issue_access_token(user_id=123, scope="api")
    payload = service.decode_token(token=token)

    assert payload["sub"] == "123"
    assert payload["typ"] == "test+jwt"
    assert payload["scope"] == "api"


def test_jwt_service_exposes_invalid_token_error_contract() -> None:
    service = JWTService(_settings=JWTServiceSettings(secret_key=SecretStr(_SECRET_KEY)))

    with pytest.raises(JWTService.INVALID_TOKEN_ERROR):
        service.decode_token(token=_INVALID_TOKEN)
