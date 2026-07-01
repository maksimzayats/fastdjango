from datetime import UTC, datetime

from fastapi_template.core.authentication.entities.refresh_session import RefreshSession
from fastapi_template.core.authentication.infrastructure.sqlalchemy.models.refresh_session import (
    RefreshSessionModel,
)
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.infrastructure.sqlalchemy.mappers.user import user_from_model


def refresh_session_from_model(
    *,
    model: RefreshSessionModel,
    user: User | None = None,
) -> RefreshSession:
    """Map a SQLAlchemy refresh-session model to a core entity.

    Returns:
        The mapped refresh-session entity.
    """
    return RefreshSession(
        id=model.id,
        refresh_token_hash=model.refresh_token_hash,
        user=user or user_from_model(model=model.user),
        user_agent=model.user_agent,
        ip_address_trace=model.ip_address_trace,
        created_at=_ensure_aware_datetime(datetime_value=model.created_at),
        last_used_at=_optional_aware_datetime(datetime_value=model.last_used_at),
        expires_at=_ensure_aware_datetime(datetime_value=model.expires_at),
        revoked_at=_optional_aware_datetime(datetime_value=model.revoked_at),
        rotation_counter=model.rotation_counter,
    )


def _ensure_aware_datetime(*, datetime_value: datetime) -> datetime:
    if datetime_value.tzinfo is None:
        return datetime_value.replace(tzinfo=UTC)

    return datetime_value


def _optional_aware_datetime(*, datetime_value: datetime | None) -> datetime | None:
    if datetime_value is None:
        return None

    return _ensure_aware_datetime(datetime_value=datetime_value)
