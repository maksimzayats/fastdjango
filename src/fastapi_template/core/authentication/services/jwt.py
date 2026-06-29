from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import jwt
from diwire import Injected
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi_template.foundation.service import BaseService


class JWTServiceSettings(BaseSettings):
    """JWT signing settings loaded from the runtime environment."""

    model_config = SettingsConfigDict(env_prefix="JWT_")

    secret_key: SecretStr
    algorithm: str = "HS256"
    typ: str = "at+jwt"
    access_token_expire_minutes: int = 15

    @property
    def access_token_expire(self) -> timedelta:
        """Convert the configured access-token lifetime to a timedelta.

        Returns:
            Access-token lifetime used in the JWT ``exp`` claim.
        """
        return timedelta(minutes=self.access_token_expire_minutes)


@dataclass(kw_only=True)
class JWTService(BaseService):
    """Issue and decode signed access tokens for authenticated users."""

    EXPIRED_SIGNATURE_ERROR: ClassVar = jwt.ExpiredSignatureError  # noqa: WPS115
    INVALID_TOKEN_ERROR: ClassVar = jwt.InvalidTokenError  # noqa: WPS115

    _settings: Injected[JWTServiceSettings]

    def issue_access_token(
        self,
        *,
        user_id: Any,
        **payload_kwargs: Any,
    ) -> str:
        """Create a signed access token containing the user subject.

        Returns:
            Encoded JWT string ready for HTTP responses.
        """
        iat = datetime.now(tz=UTC)
        payload = {
            **payload_kwargs,
            "sub": str(user_id),
            "exp": iat + self._settings.access_token_expire,
            "iat": iat,
            "typ": self._settings.typ,
        }

        return jwt.encode(
            payload=payload,
            key=self._settings.secret_key.get_secret_value(),
            algorithm=self._settings.algorithm,
        )

    def decode_token(self, *, token: str) -> dict[str, Any]:
        """Verify and decode a JWT using the configured signing settings.

        Returns:
            Token payload after signature, expiry, and algorithm validation.
        """
        payload = jwt.decode(
            jwt=token,
            key=self._settings.secret_key.get_secret_value(),
            algorithms=[self._settings.algorithm],
        )
        if payload.get("typ") != self._settings.typ:
            raise self.INVALID_TOKEN_ERROR

        return payload
