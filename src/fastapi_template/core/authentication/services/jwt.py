from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import jwt
from diwire import Injected
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi_template.foundation.service import BaseService


class JWTServiceSettings(BaseSettings):
    """Define JWTServiceSettings."""

    model_config = SettingsConfigDict(env_prefix="JWT_")

    secret_key: SecretStr
    algorithm: str = "HS256"
    typ: str = "at+jwt"
    access_token_expire_minutes: int = 15

    @property
    def access_token_expire(self) -> timedelta:
        """Run access token expire.

        Returns:
        The operation result.
        """
        return timedelta(minutes=self.access_token_expire_minutes)


@dataclass(kw_only=True)
class JWTService(BaseService):
    """Define JWTService."""

    EXPIRED_SIGNATURE_ERROR: ClassVar = jwt.ExpiredSignatureError
    INVALID_TOKEN_ERROR: ClassVar = jwt.InvalidTokenError

    _settings: Injected[JWTServiceSettings]

    def issue_access_token(
        self,
        *,
        user_id: Any,
        **payload_kwargs: Any,
    ) -> str:
        """Run issue access token.

        Returns:
        The operation result.
        """
        iat = datetime.now(tz=UTC)
        payload = {
            "sub": str(user_id),
            "exp": iat + self._settings.access_token_expire,
            "iat": iat,
            "typ": self._settings.typ,
            **payload_kwargs,
        }

        return jwt.encode(
            payload=payload,
            key=self._settings.secret_key.get_secret_value(),
            algorithm=self._settings.algorithm,
        )

    def decode_token(self, *, token: str) -> dict[str, Any]:
        """Run decode token.

        Returns:
        The operation result.
        """
        return jwt.decode(
            jwt=token,
            key=self._settings.secret_key.get_secret_value(),
            algorithms=[self._settings.algorithm],
        )
