import hashlib
from dataclasses import dataclass, field
from typing import Any, Self, cast

import pytest

from fastdjango.core.authentication.models import RefreshSession
from fastdjango.core.authentication.services.refresh_session import (
    RefreshSessionService,
    RefreshSessionServiceSettings,
)

_OLD_REFRESH_TOKEN = "old-refresh-token"  # noqa: S105


@dataclass
class FakeUser:
    pk: int = 1


@dataclass
class FakeRefreshSession:
    user: FakeUser = field(default_factory=FakeUser)
    refresh_token_hash: str = ""
    rotation_counter: int = 0
    last_used_at: object | None = None
    revoked_at: object | None = None
    is_active: bool = True
    saved_update_fields: list[str] | None = None

    def save(self, *, update_fields: list[str]) -> None:
        self.saved_update_fields = update_fields


@dataclass
class FakeRefreshSessionQuerySet:
    session: FakeRefreshSession
    selected_for_update: bool = False
    lookup: dict[str, str] | None = None

    def select_for_update(self) -> Self:
        self.selected_for_update = True
        return self

    def get(self, **kwargs: str) -> RefreshSession:
        self.lookup = kwargs
        return cast(RefreshSession, self.session)


@dataclass
class FakeRefreshSessionManager:
    queryset: FakeRefreshSessionQuerySet

    def all(self) -> FakeRefreshSessionQuerySet:
        return self.queryset


def test_rotate_refresh_token_locks_session_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RefreshSessionService(_settings=RefreshSessionServiceSettings())
    session = FakeRefreshSession()
    queryset = FakeRefreshSessionQuerySet(session=session)
    monkeypatch.setattr(
        RefreshSession,
        "objects",
        FakeRefreshSessionManager(queryset=queryset),
    )

    cast(Any, service.rotate_refresh_token).__wrapped__(
        service,
        _OLD_REFRESH_TOKEN,
    )

    assert queryset.selected_for_update is True
    assert queryset.lookup == {
        "refresh_token_hash": hashlib.sha256(_OLD_REFRESH_TOKEN.encode()).hexdigest(),
    }
    assert session.rotation_counter == 1
    assert session.saved_update_fields == [
        "refresh_token_hash",
        "rotation_counter",
        "last_used_at",
    ]


def test_revoke_refresh_token_locks_session_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = RefreshSessionService(_settings=RefreshSessionServiceSettings())
    session = FakeRefreshSession()
    queryset = FakeRefreshSessionQuerySet(session=session)
    monkeypatch.setattr(
        RefreshSession,
        "objects",
        FakeRefreshSessionManager(queryset=queryset),
    )

    cast(Any, service.revoke_refresh_token).__wrapped__(
        service,
        _OLD_REFRESH_TOKEN,
        session.user,
    )

    assert queryset.selected_for_update is True
    assert queryset.lookup == {
        "refresh_token_hash": hashlib.sha256(_OLD_REFRESH_TOKEN.encode()).hexdigest(),
    }
    assert session.revoked_at is not None
    assert session.saved_update_fields == ["revoked_at"]
