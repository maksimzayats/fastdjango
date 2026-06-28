import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from fastapi_template.core.user.infrastructure.persistence.sqlalchemy.models import UserModel
from fastapi_template.infrastructure.database.base import Base

REFRESH_TOKEN_HASH_LENGTH = 128


class RefreshSessionModel(Base):
    """Define RefreshSessionModel."""

    __tablename__ = "refresh_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(length=REFRESH_TOKEN_HASH_LENGTH),
        unique=True,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    user_agent: Mapped[str] = mapped_column(Text, default="")
    ip_address_trace: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    rotation_counter: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped[UserModel] = relationship(back_populates="refresh_sessions")
