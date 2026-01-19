from dataclasses import dataclass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from core.user.models import User


@dataclass(kw_only=True)
class UserService:
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
        password: str,
        *,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
    ) -> bool:
        """Validate the strength of the given password.

        Returns True if the password is strong enough, False otherwise.
        """
        try:
            validate_password(
                password=password,
                user=User(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                ),
            )
        except ValidationError:
            return False

        return True

    def create_user(
        self,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
        password: str,
    ) -> User:
        return User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
        )
