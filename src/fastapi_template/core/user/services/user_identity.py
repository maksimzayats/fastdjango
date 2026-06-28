import unicodedata
from dataclasses import dataclass

from fastapi_template.core.user.dtos.create_user import CreateUserDTO
from fastapi_template.foundation.service import BaseService


@dataclass(kw_only=True)
class UserIdentityService(BaseService):
    """Define UserIdentityService."""

    def normalize_create_user_data(self, *, data: CreateUserDTO) -> CreateUserDTO:
        """Run normalize create user data.

        Returns:
        The operation result.
        """
        return CreateUserDTO(
            username=self.normalize_username(username=data.username),
            email=self.normalize_email(email=str(data.email)),
            first_name=data.first_name,
            last_name=data.last_name,
            password=data.password,
        )

    def normalize_username(self, *, username: str) -> str:
        """Run normalize username.

        Returns:
        The operation result.
        """
        return unicodedata.normalize("NFKC", username.strip())

    def normalize_email(self, *, email: str) -> str:
        """Run normalize email.

        Returns:
        The operation result.
        """
        local_part, separator, domain = email.strip().partition("@")
        if not separator:
            return email.strip()

        return f"{local_part}@{domain.casefold()}"
