from dataclasses import dataclass, field
from typing import ClassVar

from diwire import Injected
from pwdlib import PasswordHash
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi_template.core.user.dtos.create_user import CreateUserDTO
from fastapi_template.core.user.exceptions.weak_password import WeakPasswordError
from fastapi_template.foundation.service import BaseService


class PasswordServiceSettings(BaseSettings):
    """Define PasswordServiceSettings."""

    model_config = SettingsConfigDict(env_prefix="PASSWORD_")

    min_length: int = 8
    max_length: int = 128


@dataclass(kw_only=True)
class PasswordService(BaseService):
    """Define PasswordService."""

    WEAK_PASSWORD_ERROR: ClassVar = WeakPasswordError

    _settings: Injected[PasswordServiceSettings]

    _password_hash: PasswordHash = field(init=False)

    def __post_init__(self) -> None:
        """Run post init."""
        self._password_hash = PasswordHash.recommended()

    def validate(self, *, data: CreateUserDTO) -> None:
        """Run validate."""
        if self._is_weak_password(data=data):
            raise self.WEAK_PASSWORD_ERROR

    def hash_password(self, *, password: str) -> str:
        """Run hash password.

        Returns:
        The operation result.
        """
        return self._password_hash.hash(password)

    def verify_password(self, *, password: str, password_hash: str) -> bool:
        """Run verify password.

        Returns:
        The operation result.
        """
        return self._password_hash.verify(password, password_hash)

    def _is_weak_password(self, *, data: CreateUserDTO) -> bool:
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
