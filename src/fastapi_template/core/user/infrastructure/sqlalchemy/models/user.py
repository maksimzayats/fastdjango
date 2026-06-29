from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_template.infrastructure.sqlalchemy.base import Base

EMAIL_MAX_LENGTH = 320
NAME_MAX_LENGTH = 150
PASSWORD_HASH_MAX_LENGTH = 255


class UserModel(Base):
    """SQLAlchemy table mapping for core user accounts."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(length=NAME_MAX_LENGTH))
    email: Mapped[str] = mapped_column(String(length=EMAIL_MAX_LENGTH))
    first_name: Mapped[str] = mapped_column(String(length=NAME_MAX_LENGTH))
    last_name: Mapped[str] = mapped_column(String(length=NAME_MAX_LENGTH))
    password_hash: Mapped[str] = mapped_column(String(length=PASSWORD_HASH_MAX_LENGTH))
    is_active: Mapped[bool] = mapped_column(Boolean)
    is_staff: Mapped[bool] = mapped_column(Boolean)
    is_superuser: Mapped[bool] = mapped_column(Boolean)
