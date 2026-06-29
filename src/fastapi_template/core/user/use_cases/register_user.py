from dataclasses import dataclass
from typing import ClassVar

from diwire import Injected

from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.dtos.persist_user import PersistUserDTO
from fastapi_template.core.user.dtos.register_user import RegisterUserDTO
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.exceptions.user_already_exists import UserAlreadyExistsError
from fastapi_template.core.user.exceptions.user_repository_conflict import (
    UserRepositoryConflictError,
)
from fastapi_template.core.user.exceptions.weak_password import WeakPasswordError
from fastapi_template.core.user.services.password import PasswordService
from fastapi_template.core.user.services.user_identity import UserIdentityService
from fastapi_template.foundation.use_case import BaseUseCase


@dataclass(kw_only=True)
class RegisterUserUseCase(BaseUseCase):
    """Register a normal user account from untrusted public input."""

    WEAK_PASSWORD_ERROR: ClassVar = WeakPasswordError  # noqa: WPS115
    USER_ALREADY_EXISTS_ERROR: ClassVar = UserAlreadyExistsError  # noqa: WPS115
    USER_REPOSITORY_CONFLICT_ERROR: ClassVar = UserRepositoryConflictError  # noqa: WPS115

    _identity_service: Injected[UserIdentityService]
    _password_service: Injected[PasswordService]
    _uow: Injected[UnitOfWork]

    async def execute(self, *, data: RegisterUserDTO) -> User:
        """Validate public registration data and persist a non-privileged account.

        Returns:
            The created user entity with only default account privileges.
        """
        normalized_data = self._identity_service.normalize_register_user_data(data=data)
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
                    data=_persist_user_data(data=normalized_data),
                    password_hash=password_hash,
                )
            except self.USER_REPOSITORY_CONFLICT_ERROR as exception:
                raise self.USER_ALREADY_EXISTS_ERROR from exception


def _persist_user_data(*, data: RegisterUserDTO) -> PersistUserDTO:
    return PersistUserDTO(
        email=data.email,
        username=data.username,
        first_name=data.first_name,
        last_name=data.last_name,
        password=data.password,
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )
