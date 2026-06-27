from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractUser
from django.db import models

if TYPE_CHECKING:
    from modern_python_template.core.authentication.models import RefreshSession


class User(AbstractUser):
    # Keep this quoted so User.__annotations__ does not evaluate TYPE_CHECKING imports.
    refresh_sessions: "models.Manager[RefreshSession]"  # noqa: UP037

    email = models.EmailField(verbose_name="email address", unique=True)

    def __str__(self) -> str:
        return f"User(id={self.pk}, username={self.username})"
