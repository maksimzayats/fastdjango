import uuid
from datetime import UTC, datetime, timedelta

import pytest
from diwire import Container

from fastapi_template.core.authentication.dtos.create_refresh_session import (
    CreateRefreshSessionDTO,
)
from fastapi_template.core.authentication.dtos.replace_refresh_session_token import (
    ReplaceRefreshSessionTokenDTO,
)
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.dtos.create_user import CreateUserDTO
from fastapi_template.core.user.entities.user import User


@pytest.mark.anyio
async def test_refresh_session_repository_returns_none_for_missing_session(
    container: Container,
) -> None:
    uow = container.resolve(UnitOfWork)

    async with uow as active_uow:
        assert (
            await active_uow.refresh_session_repository.get_by_token_hash(
                refresh_token_hash=_refresh_hash("missing"),
            )
            is None
        )
        assert (
            await active_uow.refresh_session_repository.replace_token_hash(
                data=ReplaceRefreshSessionTokenDTO(
                    session_id=_missing_uuid(),
                    expected_refresh_token_hash=_refresh_hash("old"),
                    refresh_token_hash=_refresh_hash("new"),
                    last_used_at=datetime.now(tz=UTC),
                    rotation_counter=1,
                ),
            )
            is None
        )

        await active_uow.refresh_session_repository.revoke(
            session_id=_missing_uuid(),
            revoked_at=datetime.now(tz=UTC),
        )


@pytest.mark.anyio
async def test_refresh_session_repository_creates_and_updates_session(
    container: Container,
) -> None:
    uow = container.resolve(UnitOfWork)

    async with uow as active_uow:
        user = await active_uow.user_repository.create(
            data=_create_user_data(username="session_user", email="session@example.com"),
            password_hash=_password_hash(),
        )
        session = await active_uow.refresh_session_repository.create(
            data=_create_refresh_session_data(
                user=user,
                refresh_token_hash=_refresh_hash("old"),
                user_agent="test-agent",
                ip_address_trace="127.0.0.1",
            ),
        )
        updated_session = await active_uow.refresh_session_repository.replace_token_hash(
            data=ReplaceRefreshSessionTokenDTO(
                session_id=session.id,
                expected_refresh_token_hash=_refresh_hash("old"),
                refresh_token_hash=_refresh_hash("new"),
                last_used_at=datetime.now(tz=UTC),
                rotation_counter=session.rotation_counter + 1,
            ),
        )
        stale_session = await active_uow.refresh_session_repository.replace_token_hash(
            data=ReplaceRefreshSessionTokenDTO(
                session_id=session.id,
                expected_refresh_token_hash=_refresh_hash("old"),
                refresh_token_hash=_refresh_hash("stale"),
                last_used_at=datetime.now(tz=UTC),
                rotation_counter=2,
            ),
        )

    assert updated_session is not None
    assert updated_session.refresh_token_hash == _refresh_hash("new")
    assert updated_session.rotation_counter == 1
    assert stale_session is None


@pytest.mark.anyio
async def test_refresh_session_repository_updates_matching_session_without_active_policy(
    container: Container,
) -> None:
    uow = container.resolve(UnitOfWork)

    async with uow as active_uow:
        user = await active_uow.user_repository.create(
            data=_create_user_data(username="inactive_user", email="inactive@example.com"),
            password_hash=_password_hash(),
        )
        expired_session = await active_uow.refresh_session_repository.create(
            data=_create_refresh_session_data(
                user=user,
                refresh_token_hash=_refresh_hash("expired"),
                user_agent="test-agent",
                ip_address_trace="127.0.0.1",
                expires_at=datetime.now(tz=UTC) - timedelta(seconds=1),
            ),
        )
        revoked_session = await active_uow.refresh_session_repository.create(
            data=_create_refresh_session_data(
                user=user,
                refresh_token_hash=_refresh_hash("revoked"),
                user_agent="test-agent",
                ip_address_trace="127.0.0.1",
            ),
        )
        await active_uow.refresh_session_repository.revoke(
            session_id=revoked_session.id,
            revoked_at=datetime.now(tz=UTC),
        )

        expired_result = await active_uow.refresh_session_repository.replace_token_hash(
            data=ReplaceRefreshSessionTokenDTO(
                session_id=expired_session.id,
                expected_refresh_token_hash=expired_session.refresh_token_hash,
                refresh_token_hash=_refresh_hash("expired-new"),
                last_used_at=datetime.now(tz=UTC),
                rotation_counter=expired_session.rotation_counter + 1,
            ),
        )
        revoked_result = await active_uow.refresh_session_repository.replace_token_hash(
            data=ReplaceRefreshSessionTokenDTO(
                session_id=revoked_session.id,
                expected_refresh_token_hash=revoked_session.refresh_token_hash,
                refresh_token_hash=_refresh_hash("revoked-new"),
                last_used_at=datetime.now(tz=UTC),
                rotation_counter=revoked_session.rotation_counter + 1,
            ),
        )

    assert expired_result is not None
    assert revoked_result is not None


def _create_user_data(
    *,
    username: str,
    email: str,
) -> CreateUserDTO:
    return CreateUserDTO(
        username=username,
        email=email,
        first_name="Repository",
        last_name="User",
        password=_valid_password(),
    )


def _create_refresh_session_data(
    *,
    user: User,
    refresh_token_hash: str,
    user_agent: str,
    ip_address_trace: str,
    expires_at: datetime | None = None,
) -> CreateRefreshSessionDTO:
    created_at = datetime.now(tz=UTC)
    return CreateRefreshSessionDTO(
        user=user,
        refresh_token_hash=refresh_token_hash,
        user_agent=user_agent,
        ip_address_trace=ip_address_trace,
        created_at=created_at,
        last_used_at=None,
        expires_at=expires_at or created_at + timedelta(days=1),
        revoked_at=None,
        rotation_counter=0,
    )


def _missing_uuid() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000000")


def _password_hash() -> str:
    return "argon2-hash-value"


def _refresh_hash(value: str) -> str:
    return f"refresh-hash-{value}"


def _valid_password() -> str:
    return "S3cure-test-value-123!"
