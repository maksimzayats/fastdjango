from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar

import jwt
from diwire import Injected
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastdjango.foundation.services import BaseService


class JWTServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JWT_")

    secret_key: SecretStr | None = None
    algorithm: str = "HS256"
    typ: str = "at+jwt"
    access_token_expire_minutes: int = 15

    @property
    def access_token_expire(self) -> timedelta:
        return timedelta(minutes=self.access_token_expire_minutes)


@dataclass(kw_only=True)
class JWTService(BaseService):
    EXPIRED_SIGNATURE_ERROR: ClassVar = jwt.ExpiredSignatureError
    INVALID_TOKEN_ERROR: ClassVar = jwt.InvalidTokenError
    MISSING_SECRET_KEY_ERROR: ClassVar = ValueError

    _settings: Injected[JWTServiceSettings]

    def issue_access_token(
        self,
        *,
        user_id: Any,
        **payload_kwargs: Any,
    ) -> str:
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
            key=self._secret_key,
            algorithm=self._settings.algorithm,
        )

    def decode_token(self, *, token: str) -> dict[str, Any]:
        return jwt.decode(
            jwt=token,
            key=self._secret_key,
            algorithms=[self._settings.algorithm],
        )

    @property
    def _secret_key(self) -> str:
        if self._settings.secret_key is None:
            msg = "JWT_SECRET_KEY is required when AUTHENTICATION_MODE=jwt-refresh-session."
            raise self.MISSING_SECRET_KEY_ERROR(msg)

        return self._settings.secret_key.get_secret_value()
