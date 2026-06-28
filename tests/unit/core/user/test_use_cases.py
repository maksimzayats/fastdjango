from dataclasses import dataclass, field
from types import TracebackType

import pytest

from fastapi_template.core.authentication.repositories import RefreshSessionRepository
from fastapi_template.core.health.repositories import HealthRepository
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.dtos import CreateUserDTO
from fastapi_template.core.user.entities import User
from fastapi_template.core.user.exceptions import UserAlreadyExistsError
from fastapi_template.core.user.repositories import UserRepository
from fastapi_template.core.user.services import (
    PasswordService,
    PasswordServiceSettings,
    UserIdentityService,
)
from fastapi_template.core.user.use_cases import (
    CreateUserUseCase,
    GetActiveUserByIdUseCase,
    GetUserByIdUseCase,
)

_STRONG_PASSWORD = "S3cure-test-password-123!"  # noqa: S105
_WEAK_PASSWORD = "123"  # noqa: S105


class UnexpectedRepositoryAccessError(Exception):
    pass


@dataclass
class FakeUserRepository(UserRepository):
    users: list[User] = field(default_factory=list)
    create_error: Exception | None = None
    created_password_hash: str | None = None

    async def get_by_id(self, *, user_id: int) -> User | None:
        return next((user for user in self.users if user.id == user_id), None)

    async def get_active_by_id(self, *, user_id: int) -> User | None:
        return next(
            (user for user in self.users if user.id == user_id and user.is_active),
            None,
        )

    async def get_by_username(self, *, username: str) -> User | None:
        return next((user for user in self.users if user.username == username), None)

    async def get_by_username_or_email(self, *, username: str, email: str) -> User | None:
        return next(
            (user for user in self.users if user.username == username or user.email == email),
            None,
        )

    async def create(self, *, data: CreateUserDTO, password_hash: str) -> User:
        if self.create_error is not None:
            raise self.create_error

        self.created_password_hash = password_hash
        user = User(
            id=len(self.users) + 1,
            username=data.username,
            email=str(data.email),
            first_name=data.first_name,
            last_name=data.last_name,
            password_hash=password_hash,
        )
        self.users.append(user)
        return user

    async def set_access_flags(
        self,
        *,
        user_id: int,
        is_staff: bool,
        is_superuser: bool,
    ) -> User | None:
        user = await self.get_by_id(user_id=user_id)
        if user is None:
            return None

        updated_user = User(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            password_hash=user.password_hash,
            is_active=user.is_active,
            is_staff=is_staff,
            is_superuser=is_superuser,
        )
        self.users = [existing_user for existing_user in self.users if existing_user.id != user.id]
        self.users.append(updated_user)
        return updated_user


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

    @property
    def health_repository(self) -> HealthRepository:
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
async def test_create_user_rejects_weak_password() -> None:
    use_case = _build_use_case()

    with pytest.raises(CreateUserUseCase.WEAK_PASSWORD_ERROR):
        await use_case.execute(data=_create_user_dto(password=_WEAK_PASSWORD))


@pytest.mark.anyio
async def test_create_user_maps_repository_duplicate_error() -> None:
    use_case = _build_use_case(
        repository=FakeUserRepository(create_error=UserAlreadyExistsError()),
    )

    with pytest.raises(CreateUserUseCase.USER_ALREADY_EXISTS_ERROR):
        await use_case.execute(data=_create_user_dto())


@pytest.mark.anyio
async def test_create_user_hashes_password_before_persisting() -> None:
    repository = FakeUserRepository()
    use_case = _build_use_case(repository=repository)

    user = await use_case.execute(data=_create_user_dto())

    assert user.username == "new_user"
    assert repository.created_password_hash is not None
    assert repository.created_password_hash != _STRONG_PASSWORD


@pytest.mark.anyio
async def test_create_user_normalizes_identity_before_persisting() -> None:
    repository = FakeUserRepository()
    use_case = _build_use_case(repository=repository)

    user = await use_case.execute(
        data=_create_user_dto(username=" new_user ", email="new_user@EXAMPLE.COM"),
    )

    assert user.username == "new_user"
    assert user.email == "new_user@example.com"


@pytest.mark.anyio
async def test_create_user_rejects_existing_normalized_username_or_email() -> None:
    repository = FakeUserRepository(
        users=[
            User(
                id=1,
                username="existing_user",
                email="existing@example.com",
                first_name="Existing",
                last_name="User",
                password_hash=_stored_secret_hash(),
            ),
        ],
    )
    use_case = _build_use_case(repository=repository)

    with pytest.raises(CreateUserUseCase.USER_ALREADY_EXISTS_ERROR):
        await use_case.execute(
            data=_create_user_dto(username=" existing_user ", email="new@example.com"),
        )


@pytest.mark.anyio
async def test_get_user_by_id_returns_matching_user() -> None:
    user = _build_user(user_id=1)
    repository = FakeUserRepository(users=[user])
    use_case = GetUserByIdUseCase(_uow=FakeUnitOfWork(_user_repository=repository))

    assert await use_case.execute(user_id=user.id) == user


@pytest.mark.anyio
async def test_get_active_user_by_id_ignores_inactive_user() -> None:
    user = _build_user(user_id=1, is_active=False)
    repository = FakeUserRepository(users=[user])
    use_case = GetActiveUserByIdUseCase(_uow=FakeUnitOfWork(_user_repository=repository))

    assert await use_case.execute(user_id=user.id) is None


def _build_use_case(repository: FakeUserRepository | None = None) -> CreateUserUseCase:
    return CreateUserUseCase(
        _identity_service=UserIdentityService(),
        _password_service=PasswordService(_settings=PasswordServiceSettings()),
        _uow=FakeUnitOfWork(_user_repository=repository or FakeUserRepository()),
    )


def _create_user_dto(
    *,
    username: str = "new_user",
    email: str = "new_user@example.com",
    password: str = _STRONG_PASSWORD,
) -> CreateUserDTO:
    return CreateUserDTO(
        username=username,
        email=email,
        first_name="New",
        last_name="User",
        password=password,
    )


def _stored_secret_hash() -> str:
    return "hash"


def _build_user(*, user_id: int, is_active: bool = True) -> User:
    return User(
        id=user_id,
        username="test_user",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=_stored_secret_hash(),
        is_active=is_active,
    )
