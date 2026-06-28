from abc import ABC, abstractmethod
from typing import ClassVar

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_template.core.user.dtos import CreateUserDTO
from fastapi_template.core.user.entities import User
from fastapi_template.core.user.exceptions import UserAlreadyExistsError
from fastapi_template.core.user.models import UserModel


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, *, user_id: int) -> User | None: ...

    @abstractmethod
    async def get_active_by_id(self, *, user_id: int) -> User | None: ...

    @abstractmethod
    async def get_by_username(self, *, username: str) -> User | None: ...

    @abstractmethod
    async def get_by_username_or_email(self, *, username: str, email: str) -> User | None: ...

    @abstractmethod
    async def create(self, *, data: CreateUserDTO, password_hash: str) -> User: ...

    @abstractmethod
    async def set_access_flags(
        self,
        *,
        user_id: int,
        is_staff: bool,
        is_superuser: bool,
    ) -> User | None: ...


class SQLAlchemyUserRepository(UserRepository):
    USER_ALREADY_EXISTS_ERROR: ClassVar = UserAlreadyExistsError
    INTEGRITY_ERROR: ClassVar = IntegrityError

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, *, user_id: int) -> User | None:
        model = await self._session.get(UserModel, user_id)

        if model is None:
            return None

        return user_from_model(model=model)

    async def get_active_by_id(self, *, user_id: int) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(
                UserModel.id == user_id,
                UserModel.is_active.is_(True),
            ),
        )
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return user_from_model(model=model)

    async def get_by_username(self, *, username: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.username == username),
        )
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return user_from_model(model=model)

    async def get_by_username_or_email(self, *, username: str, email: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(
                or_(
                    UserModel.username == username,
                    UserModel.email == email,
                ),
            ),
        )
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return user_from_model(model=model)

    async def create(self, *, data: CreateUserDTO, password_hash: str) -> User:
        model = UserModel(
            username=data.username,
            email=str(data.email),
            first_name=data.first_name,
            last_name=data.last_name,
            password_hash=password_hash,
        )

        try:
            self._session.add(model)
            await self._session.flush()
        except self.INTEGRITY_ERROR as e:
            raise self.USER_ALREADY_EXISTS_ERROR from e

        return user_from_model(model=model)

    async def set_access_flags(
        self,
        *,
        user_id: int,
        is_staff: bool,
        is_superuser: bool,
    ) -> User | None:
        model = await self._session.get(UserModel, user_id)
        if model is None:
            return None

        model.is_staff = is_staff
        model.is_superuser = is_superuser
        await self._session.flush()

        return user_from_model(model=model)


def user_from_model(*, model: UserModel) -> User:
    return User(
        id=model.id,
        username=model.username,
        email=model.email,
        first_name=model.first_name,
        last_name=model.last_name,
        password_hash=model.password_hash,
        is_active=model.is_active,
        is_staff=model.is_staff,
        is_superuser=model.is_superuser,
    )
