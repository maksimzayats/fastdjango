import unicodedata
from dataclasses import dataclass, field
from typing import ClassVar

from diwire import Injected
from pwdlib import PasswordHash
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.dtos import CreateUserDTO
from fastapi_template.core.user.entities import User
from fastapi_template.core.user.exceptions import WeakPasswordError
from fastapi_template.foundation.services import BaseService


@dataclass(kw_only=True)
class UserIdentityService(BaseService):
    def normalize_create_user_data(self, *, data: CreateUserDTO) -> CreateUserDTO:
        return CreateUserDTO(
            username=self.normalize_username(username=data.username),
            email=self.normalize_email(email=str(data.email)),
            first_name=data.first_name,
            last_name=data.last_name,
            password=data.password,
        )

    def normalize_username(self, *, username: str) -> str:
        return unicodedata.normalize("NFKC", username.strip())

    def normalize_email(self, *, email: str) -> str:
        local_part, separator, domain = email.strip().partition("@")
        if not separator:
            return email.strip()

        return f"{local_part}@{domain.casefold()}"


class PasswordServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PASSWORD_")

    min_length: int = 8
    max_length: int = 128


@dataclass(kw_only=True)
class PasswordService(BaseService):
    WEAK_PASSWORD_ERROR: ClassVar = WeakPasswordError

    _settings: Injected[PasswordServiceSettings]

    _password_hash: PasswordHash = field(init=False)

    def __post_init__(self) -> None:
        self._password_hash = PasswordHash.recommended()

    def validate(self, *, data: CreateUserDTO) -> None:
        password = data.password
        if len(password) < self._settings.min_length:
            raise self.WEAK_PASSWORD_ERROR

        if len(password) > self._settings.max_length:
            raise self.WEAK_PASSWORD_ERROR

        if password.isnumeric():
            raise self.WEAK_PASSWORD_ERROR

        if password.casefold() in {
            data.username.casefold(),
            str(data.email).casefold(),
        }:
            raise self.WEAK_PASSWORD_ERROR

    def hash_password(self, *, password: str) -> str:
        return self._password_hash.hash(password)

    def verify_password(self, *, password: str, password_hash: str) -> bool:
        return self._password_hash.verify(password, password_hash)


@dataclass(kw_only=True)
class UserCredentialService(BaseService):
    _identity_service: Injected[UserIdentityService]
    _password_service: Injected[PasswordService]

    async def authenticate_user(
        self,
        *,
        uow: UnitOfWork,
        username: str,
        password: str,
    ) -> User | None:
        normalized_username = self._identity_service.normalize_username(username=username)
        user = await uow.user_repository.get_by_username(username=normalized_username)
        if user is None:
            return None

        is_valid_password = self._password_service.verify_password(
            password=password,
            password_hash=user.password_hash,
        )
        if not is_valid_password:
            return None

        return user
