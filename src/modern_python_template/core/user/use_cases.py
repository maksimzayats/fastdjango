from dataclasses import dataclass
from typing import ClassVar

from asgiref.sync import sync_to_async
from diwire import Injected
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from modern_python_template.core.user.dtos import CreateUserDTO
from modern_python_template.core.user.exceptions import UserAlreadyExistsError, WeakPasswordError
from modern_python_template.core.user.models import User
from modern_python_template.foundation.transactions import TransactionFactory
from modern_python_template.foundation.use_cases import BaseUseCase


@dataclass(kw_only=True)
class UserUseCase(BaseUseCase):
    USER_NOT_FOUND_ERROR: ClassVar = User.DoesNotExist
    PASSWORD_VALIDATION_ERROR: ClassVar = ValidationError
    WEAK_PASSWORD_ERROR: ClassVar = WeakPasswordError
    USER_ALREADY_EXISTS_ERROR: ClassVar = UserAlreadyExistsError
    INTEGRITY_ERROR: ClassVar = IntegrityError

    _transaction_factory: Injected[TransactionFactory]

    async def get_user_by_id(self, *, user_id: int) -> User | None:
        return await User.objects.filter(id=user_id).afirst()

    async def get_active_user_by_id(self, *, user_id: int) -> User | None:
        return await User.objects.filter(id=user_id, is_active=True).afirst()

    async def get_user_by_username_and_password(
        self,
        *,
        username: str,
        password: str,
    ) -> User | None:
        return await sync_to_async(
            self._get_user_by_username_and_password,
            thread_sensitive=True,
        )(username=username, password=password)

    def _get_user_by_username_and_password(
        self,
        *,
        username: str,
        password: str,
    ) -> User | None:
        try:
            user = User.objects.get(username=username)
        except self.USER_NOT_FOUND_ERROR:
            return None

        if not user.check_password(password):
            return None

        return user

    async def get_user_by_username_or_email(
        self,
        *,
        username: str,
        email: str,
    ) -> User | None:
        return await (
            User.objects.filter(username=username) | User.objects.filter(email=email)
        ).afirst()

    def is_valid_password(
        self,
        *,
        data: CreateUserDTO,
    ) -> bool:
        """Validate the strength of the given password.

        Returns:
            True if the password is strong enough, False otherwise.
        """
        try:
            validate_password(
                password=data.password,
                user=User(
                    username=data.username,
                    email=str(data.email),
                    first_name=data.first_name,
                    last_name=data.last_name,
                ),
            )
        except self.PASSWORD_VALIDATION_ERROR:
            return False

        return True

    async def create_user(
        self,
        *,
        data: CreateUserDTO,
    ) -> User:
        return await sync_to_async(
            self._create_user_transactionally,
            thread_sensitive=True,
        )(data=data)

    def _create_user_transactionally(
        self,
        *,
        data: CreateUserDTO,
    ) -> User:
        is_valid_password = self.is_valid_password(data=data)
        if not is_valid_password:
            raise self.WEAK_PASSWORD_ERROR

        username = User.normalize_username(data.username)
        email = User.objects.normalize_email(str(data.email))
        password = make_password(data.password)

        try:
            with self._transaction_factory(
                span_name="create user",
                use_case=type(self).__name__,
                method="_create_user_transactionally",
            ):
                existing_user = (
                    User.objects.filter(username=username) | User.objects.filter(email=email)
                ).first()
                if existing_user is not None:
                    raise self.USER_ALREADY_EXISTS_ERROR

                return User.objects.create(
                    username=username,
                    email=email,
                    first_name=data.first_name,
                    last_name=data.last_name,
                    password=password,
                )
        except self.INTEGRITY_ERROR as e:
            raise self.USER_ALREADY_EXISTS_ERROR from e
