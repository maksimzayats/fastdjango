from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fastapi_template.infrastructure.database.base import Base

EMAIL_MAX_LENGTH = 320
NAME_MAX_LENGTH = 150
PASSWORD_HASH_MAX_LENGTH = 255

if TYPE_CHECKING:
    from fastapi_template.core.authentication.infrastructure.persistence.sqlalchemy.models import (
        RefreshSessionModel,
    )


class UserModel(Base):
    """Define UserModel."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(length=NAME_MAX_LENGTH), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(length=EMAIL_MAX_LENGTH), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(length=NAME_MAX_LENGTH), default="")
    last_name: Mapped[str] = mapped_column(String(length=NAME_MAX_LENGTH), default="")
    password_hash: Mapped[str] = mapped_column(String(length=PASSWORD_HASH_MAX_LENGTH))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    refresh_sessions: Mapped[list[RefreshSessionModel]] = relationship(
        "RefreshSessionModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
