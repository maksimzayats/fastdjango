from datetime import UTC, datetime

from fastapi_template.core.authentication.entities import RefreshSession
from fastapi_template.core.authentication.infrastructure.persistence.sqlalchemy.models import (
    RefreshSessionModel,
)
from fastapi_template.core.user.entities import User
from fastapi_template.core.user.infrastructure.persistence.sqlalchemy.mappers import user_from_model


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
        created_at=ensure_aware_datetime(datetime_value=model.created_at),
        last_used_at=optional_aware_datetime(datetime_value=model.last_used_at),
        expires_at=ensure_aware_datetime(datetime_value=model.expires_at),
        revoked_at=optional_aware_datetime(datetime_value=model.revoked_at),
        rotation_counter=model.rotation_counter,
    )


def ensure_aware_datetime(*, datetime_value: datetime) -> datetime:
    """Ensure a datetime has timezone information.

    Returns:
        A timezone-aware datetime.
    """
    if datetime_value.tzinfo is None:
        return datetime_value.replace(tzinfo=UTC)

    return datetime_value


def optional_aware_datetime(*, datetime_value: datetime | None) -> datetime | None:
    """Ensure an optional datetime has timezone information.

    Returns:
        A timezone-aware datetime, or ``None`` when no value is present.
    """
    if datetime_value is None:
        return None

    return ensure_aware_datetime(datetime_value=datetime_value)
