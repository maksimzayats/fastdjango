from typing import ClassVar

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_template.core.user.dtos import CreateUserDTO
from fastapi_template.core.user.entities import User
from fastapi_template.core.user.infrastructure.persistence.sqlalchemy.mappers import user_from_model
from fastapi_template.core.user.infrastructure.persistence.sqlalchemy.models import UserModel
from fastapi_template.core.user.repositories import UserRepository


class SQLAlchemyUserRepository(UserRepository):
    """Define SQLAlchemyUserRepository."""

    INTEGRITY_ERROR: ClassVar = IntegrityError

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize the instance."""
        self._session = session

    async def get_by_id(self, *, user_id: int) -> User | None:
        """Get a user by identifier.

        Returns:
            The matching user, if one exists.
        """
        model = await self._session.get(UserModel, user_id)

        if model is None:
            return None

        return user_from_model(model=model)

    async def get_active_by_id(self, *, user_id: int) -> User | None:
        """Get an active user by identifier.

        Returns:
            The matching active user, if one exists.
        """
        query_result = await self._session.execute(
            select(UserModel).where(
                UserModel.id == user_id,
                UserModel.is_active.is_(True),
            ),
        )
        model = query_result.scalar_one_or_none()

        if model is None:
            return None

        return user_from_model(model=model)

    async def get_by_username(self, *, username: str) -> User | None:
        """Get a user by username.

        Returns:
            The matching user, if one exists.
        """
        query_result = await self._session.execute(
            select(UserModel).where(UserModel.username == username),
        )
        model = query_result.scalar_one_or_none()

        if model is None:
            return None

        return user_from_model(model=model)

    async def get_by_username_or_email(self, *, username: str, email: str) -> User | None:
        """Get a user by username or email.

        Returns:
            A matching user, if one exists.
        """
        query_result = await self._session.execute(
            select(UserModel)
            .where(
                or_(
                    UserModel.username == username,
                    UserModel.email == email,
                ),
            )
            .limit(1),
        )
        model = query_result.scalars().first()

        if model is None:
            return None

        return user_from_model(model=model)

    async def create(self, *, data: CreateUserDTO, password_hash: str) -> User:
        """Create a user.

        Returns:
            The created user.
        """
        model = UserModel(
            username=data.username,
            email=str(data.email),
            first_name=data.first_name,
            last_name=data.last_name,
            password_hash=password_hash,
        )

        self._session.add(model)
        try:
            await self._session.flush()
        except self.INTEGRITY_ERROR as exception:
            raise self.USER_ALREADY_EXISTS_ERROR from exception

        return user_from_model(model=model)

    async def set_access_flags(
        self,
        *,
        user_id: int,
        is_staff: bool,
        is_superuser: bool,
    ) -> User | None:
        """Set staff and superuser flags.

        Returns:
            The updated user, if one exists.
        """
        model = await self._session.get(UserModel, user_id)
        if model is None:
            return None

        model.is_staff = is_staff
        model.is_superuser = is_superuser
        await self._session.flush()

        return user_from_model(model=model)
