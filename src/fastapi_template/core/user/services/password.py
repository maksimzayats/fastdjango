from dataclasses import dataclass, field
from typing import ClassVar

from diwire import Injected
from pwdlib import PasswordHash
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi_template.core.user.dtos.persist_user import PersistUserDTO
from fastapi_template.core.user.dtos.register_user import RegisterUserDTO
from fastapi_template.core.user.exceptions.weak_password import WeakPasswordError
from fastapi_template.foundation.service import BaseService


class PasswordServiceSettings(BaseSettings):
    """Password policy bounds loaded from the runtime environment."""

    model_config = SettingsConfigDict(env_prefix="PASSWORD_")

    min_length: int = 8
    max_length: int = 128


@dataclass(kw_only=True)
class PasswordService(BaseService):
    """Validate passwords and delegate secure hashing to pwdlib."""

    WEAK_PASSWORD_ERROR: ClassVar = WeakPasswordError  # noqa: WPS115

    _settings: Injected[PasswordServiceSettings]

    _password_hash: PasswordHash = field(init=False)

    def __post_init__(self) -> None:
        """Create the recommended password-hashing backend once per service."""
        self._password_hash = PasswordHash.recommended()

    def validate(self, *, data: PersistUserDTO | RegisterUserDTO) -> None:
        """Reject passwords that fail the account-creation password policy."""
        if self._is_weak_password(data=data):
            raise self.WEAK_PASSWORD_ERROR

    def hash_password(self, *, password: str) -> str:
        """Hash a plaintext password with the configured pwdlib backend.

        Returns:
            Encoded password hash safe to persist.
        """
        return self._password_hash.hash(password)

    def verify_password(self, *, password: str, password_hash: str) -> bool:
        """Verify a plaintext password against a persisted hash.

        Returns:
            ``True`` when the password matches the hash.
        """
        return self._password_hash.verify(password, password_hash)

    def _is_weak_password(self, *, data: PersistUserDTO | RegisterUserDTO) -> bool:
        password = data.password

        return (
            len(password) < self._settings.min_length
            or len(password) > self._settings.max_length
            or password.isnumeric()
            or password.casefold()
            in {
                data.username.casefold(),
                str(data.email).casefold(),
            }
        )
