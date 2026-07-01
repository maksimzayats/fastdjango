from dataclasses import dataclass, field
from types import TracebackType

import pytest

from fastapi_template.core.authentication.repositories.refresh_session import (
    RefreshSessionRepository,
)
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.dtos.persist_user import PersistUserDTO
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.repositories.user import UserRepository
from fastapi_template.core.user.services.permission import UserPermissionService
from fastapi_template.core.user.use_cases.staff_user_lookup import StaffUserLookupUseCase

_PASSWORD_HASH = "hash"  # noqa: S105


class UnexpectedRepositoryAccessError(Exception):
    pass


@dataclass
class FakeUserRepository(UserRepository):
    users: list[User] = field(default_factory=list)

    async def get_by_id(self, *, user_id: int) -> User | None:
        return next((user for user in self.users if user.id == user_id), None)

    async def get_active_by_id(self, *, user_id: int) -> User | None:
        user = await self.get_by_id(user_id=user_id)
        if user is None or not user.is_active:
            return None

        return user

    async def get_by_username(self, *, username: str) -> User | None:
        raise UnexpectedRepositoryAccessError

    async def get_by_username_or_email(self, *, username: str, email: str) -> User | None:
        raise UnexpectedRepositoryAccessError

    async def create(self, *, data: PersistUserDTO, password_hash: str) -> User:
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
    entered_count: int = 0
    exited_count: int = 0
    rolled_back: bool = False

    @property
    def user_repository(self) -> UserRepository:
        return self._user_repository

    @property
    def refresh_session_repository(self) -> RefreshSessionRepository:
        raise UnexpectedRepositoryAccessError

    async def __aenter__(self) -> UnitOfWork:
        self.entered_count += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        self.exited_count += 1
        self.rolled_back = exc_type is not None
        return None


@pytest.mark.anyio
async def test_staff_user_lookup_uses_one_unit_of_work() -> None:
    actor = _build_user(user_id=1, is_staff=True)
    target = _build_user(user_id=2)
    repository = FakeUserRepository(users=[actor, target])
    uow = FakeUnitOfWork(_user_repository=repository)
    use_case = StaffUserLookupUseCase(
        _user_permission_service=UserPermissionService(),
        _uow=uow,
    )

    result = await use_case.execute(user_id=target.id, actor_user_id=actor.id)

    assert result == target
    assert uow.entered_count == 1
    assert uow.exited_count == 1
    assert uow.rolled_back is False


@pytest.mark.anyio
async def test_staff_user_lookup_rejects_missing_actor() -> None:
    target = _build_user(user_id=2)
    repository = FakeUserRepository(users=[target])
    uow = FakeUnitOfWork(_user_repository=repository)
    use_case = StaffUserLookupUseCase(
        _user_permission_service=UserPermissionService(),
        _uow=uow,
    )

    with pytest.raises(StaffUserLookupUseCase.AUTHENTICATED_USER_NOT_FOUND_ERROR):
        await use_case.execute(user_id=target.id, actor_user_id=1)

    assert uow.rolled_back is True


@pytest.mark.anyio
async def test_staff_user_lookup_rejects_non_staff_actor() -> None:
    actor = _build_user(user_id=1, is_staff=False)
    target = _build_user(user_id=2)
    repository = FakeUserRepository(users=[actor, target])
    uow = FakeUnitOfWork(_user_repository=repository)
    use_case = StaffUserLookupUseCase(
        _user_permission_service=UserPermissionService(),
        _uow=uow,
    )

    with pytest.raises(StaffUserLookupUseCase.PERMISSION_DENIED_ERROR):
        await use_case.execute(user_id=target.id, actor_user_id=actor.id)

    assert uow.rolled_back is True


def _build_user(*, user_id: int, is_staff: bool = False) -> User:
    return User(
        id=user_id,
        username=f"test_user_{user_id}",
        email=f"test-{user_id}@example.com",
        first_name="Test",
        last_name="User",
        password_hash=_PASSWORD_HASH,
        is_staff=is_staff,
    )
