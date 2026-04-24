from dataclasses import dataclass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from fastdjango.core.shared.use_cases import BaseUseCase
from fastdjango.core.user.dtos import CreateUserDTO
from fastdjango.core.user.exceptions import UserAlreadyExistsError, WeakPasswordError
from fastdjango.core.user.models import User


@dataclass(kw_only=True)
class UserUseCase(BaseUseCase):
    def get_user_by_id(self, user_id: int) -> User | None:
        return User.objects.filter(id=user_id).first()

    def get_active_user_by_id(self, user_id: int) -> User | None:
        return User.objects.filter(id=user_id, is_active=True).first()

    def get_user_by_username_and_password(
        self,
        username: str,
        password: str,
    ) -> User | None:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None

        if not user.check_password(password):
            return None

        return user

    def get_user_by_username_or_email(
        self,
        username: str,
        email: str,
    ) -> User | None:
        return (User.objects.filter(username=username) | User.objects.filter(email=email)).first()

    def is_valid_password(
        self,
        data: CreateUserDTO,
    ) -> bool:
        """Validate the strength of the given password.

        Returns True if the password is strong enough, False otherwise.
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
        except ValidationError:
            return False

        return True

    def create_user(
        self,
        data: CreateUserDTO,
    ) -> User:
        is_valid_password = self.is_valid_password(data=data)
        if not is_valid_password:
            raise WeakPasswordError

        existing_user = self.get_user_by_username_or_email(
            username=data.username,
            email=str(data.email),
        )
        if existing_user is not None:
            raise UserAlreadyExistsError

        return User.objects.create_user(
            username=data.username,
            email=str(data.email),
            first_name=data.first_name,
            last_name=data.last_name,
            password=data.password,
        )
