from dataclasses import dataclass
from typing import ClassVar

from diwire import Injected

from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.dtos import CreateUserDTO
from fastapi_template.core.user.entities import User
from fastapi_template.core.user.exceptions import UserAlreadyExistsError, WeakPasswordError
from fastapi_template.core.user.services import PasswordService, UserIdentityService
from fastapi_template.foundation.use_cases import BaseUseCase


@dataclass(kw_only=True)
class GetUserByIdUseCase(BaseUseCase):
    _uow: Injected[UnitOfWork]

    async def execute(self, *, user_id: int) -> User | None:
        async with self._uow as uow:
            return await uow.user_repository.get_by_id(user_id=user_id)


@dataclass(kw_only=True)
class GetActiveUserByIdUseCase(BaseUseCase):
    _uow: Injected[UnitOfWork]

    async def execute(self, *, user_id: int) -> User | None:
        async with self._uow as uow:
            return await uow.user_repository.get_active_by_id(user_id=user_id)


@dataclass(kw_only=True)
class CreateUserUseCase(BaseUseCase):
    WEAK_PASSWORD_ERROR: ClassVar = WeakPasswordError
    USER_ALREADY_EXISTS_ERROR: ClassVar = UserAlreadyExistsError

    _identity_service: Injected[UserIdentityService]
    _password_service: Injected[PasswordService]
    _uow: Injected[UnitOfWork]

    async def execute(self, *, data: CreateUserDTO) -> User:
        normalized_data = self._identity_service.normalize_create_user_data(data=data)
        self._password_service.validate(data=normalized_data)

        password_hash = self._password_service.hash_password(password=normalized_data.password)

        async with self._uow as uow:
            existing_user = await uow.user_repository.get_by_username_or_email(
                username=normalized_data.username,
                email=str(normalized_data.email),
            )
            if existing_user is not None:
                raise self.USER_ALREADY_EXISTS_ERROR

            try:
                return await uow.user_repository.create(
                    data=normalized_data,
                    password_hash=password_hash,
                )
            except self.USER_ALREADY_EXISTS_ERROR as e:
                raise self.USER_ALREADY_EXISTS_ERROR from e
