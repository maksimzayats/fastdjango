from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fastapi_template.core.database import Base

if TYPE_CHECKING:
    from fastapi_template.core.authentication.models import RefreshSessionModel


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(length=150), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(length=320), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(length=150), default="")
    last_name: Mapped[str] = mapped_column(String(length=150), default="")
    password_hash: Mapped[str] = mapped_column(String(length=255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)

    refresh_sessions: Mapped[list[RefreshSessionModel]] = relationship(
        "RefreshSessionModel",
        back_populates="user",
        cascade="all, delete-orphan",
    )
