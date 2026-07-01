from dataclasses import dataclass

from diwire import Injected

from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.services.password import PasswordService
from fastapi_template.core.user.services.user_identity import UserIdentityService
from fastapi_template.foundation.service import BaseService


@dataclass(kw_only=True)
class UserCredentialService(BaseService):
    """Authenticate users through repository lookup and password verification."""

    _identity_service: Injected[UserIdentityService]
    _password_service: Injected[PasswordService]

    async def authenticate_user(
        self,
        *,
        uow: UnitOfWork,
        username: str,
        password: str,
    ) -> User | None:
        """Return an active user when the supplied credentials are valid.

        Returns:
            The authenticated user, or ``None`` for invalid credentials.
        """
        normalized_username = self._identity_service.normalize_username(username=username)
        user = await uow.user_repository.get_by_username(username=normalized_username)
        if user is None:
            return None

        if not user.is_active:
            return None

        is_valid_password = self._password_service.verify_password(
            password=password,
            password_hash=user.password_hash,
        )
        if not is_valid_password:
            return None

        return user
