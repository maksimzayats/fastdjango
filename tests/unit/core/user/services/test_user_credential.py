from dataclasses import dataclass, field
from types import TracebackType

import pytest

from fastapi_template.core.authentication.repositories.refresh_session import (
    RefreshSessionRepository,
)
from fastapi_template.core.health.repositories.health import HealthRepository
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.dtos.create_user import CreateUserDTO
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.repositories.user import UserRepository
from fastapi_template.core.user.services.password import PasswordService, PasswordServiceSettings
from fastapi_template.core.user.services.user_credential import UserCredentialService
from fastapi_template.core.user.services.user_identity import UserIdentityService

_STRONG_PASSWORD = "S3cure-test-password-123!"  # noqa: S105


class UnexpectedRepositoryAccessError(Exception):
    pass


@dataclass
class FakeUserRepository(UserRepository):
    users: list[User] = field(default_factory=list)

    async def get_by_id(self, *, user_id: int) -> User | None:
        raise UnexpectedRepositoryAccessError

    async def get_active_by_id(self, *, user_id: int) -> User | None:
        raise UnexpectedRepositoryAccessError

    async def get_by_username(self, *, username: str) -> User | None:
        return next((user for user in self.users if user.username == username), None)

    async def get_by_username_or_email(self, *, username: str, email: str) -> User | None:
        raise UnexpectedRepositoryAccessError

    async def create(self, *, data: CreateUserDTO, password_hash: str) -> User:
        raise UnexpectedRepositoryAccessError

    async def set_access_flags(
        self,
        *,
        user_id: int,
        is_staff: bool,
        is_superuser: bool,
    ) -> User | None:
        raise UnexpectedRepositoryAccessError


@dataclass
class FakeUnitOfWork(UnitOfWork):
    _user_repository: UserRepository

    @property
    def user_repository(self) -> UserRepository:
        return self._user_repository

    @property
    def refresh_session_repository(self) -> RefreshSessionRepository:
        raise UnexpectedRepositoryAccessError

    @property
    def health_repository(self) -> HealthRepository:
        raise UnexpectedRepositoryAccessError

    async def __aenter__(self) -> UnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return None


@pytest.mark.anyio
async def test_user_credential_service_returns_none_for_missing_user() -> None:
    service = UserCredentialService(
        _identity_service=UserIdentityService(),
        _password_service=PasswordService(_settings=PasswordServiceSettings()),
    )
    uow = FakeUnitOfWork(_user_repository=FakeUserRepository())

    assert (
        await service.authenticate_user(
            uow=uow,
            username="missing",
            password=_STRONG_PASSWORD,
        )
        is None
    )
