from typing import cast

import pytest
from diwire import Container

from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.dtos.persist_user import PersistUserDTO
from fastapi_template.infrastructure.sqlalchemy.session import SQLAlchemySessionFactory
from fastapi_template.infrastructure.sqlalchemy.unit_of_work import SQLAlchemyUnitOfWork

_VALID_TEST_PASSWORD = "S3cure-test-password-123!"  # noqa: S105


class TransactionFailureError(Exception):
    pass


class FakeTransaction:
    async def commit(self) -> None:
        raise TransactionFailureError

    async def rollback(self) -> None:
        return None


class PassingTransaction(FakeTransaction):
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeSession:
    closed = False

    async def begin(self) -> FakeTransaction:
        return FakeTransaction()

    async def close(self) -> None:
        self.closed = True


class PassingSession(FakeSession):
    async def begin(self) -> PassingTransaction:
        return PassingTransaction()


class FakeSessionFactory:
    def __init__(self, *, session: FakeSession) -> None:
        self._session = session

    def __call__(self) -> FakeSession:
        return self._session


@pytest.mark.anyio
async def test_unit_of_work_commits_repository_changes(container: Container) -> None:
    uow = container.resolve(UnitOfWork)
    create_user_data = _persist_user_dto(username="committed_user")

    async with uow as active_uow:
        user = await active_uow.user_repository.create(
            data=create_user_data,
            password_hash=_stored_secret_hash(),
        )

    async with uow as active_uow:
        persisted_user = await active_uow.user_repository.get_by_id(user_id=user.id)

    assert persisted_user is not None
    assert persisted_user.username == create_user_data.username


@pytest.mark.anyio
async def test_unit_of_work_rolls_back_repository_changes(container: Container) -> None:
    uow = container.resolve(UnitOfWork)
    create_user_data = _persist_user_dto(username="rolled_back_user")

    with pytest.raises(TransactionFailureError):
        await _create_user_then_fail(uow=uow, data=create_user_data)

    async with uow as active_uow:
        persisted_user = await active_uow.user_repository.get_by_username(
            username=create_user_data.username,
        )

    assert persisted_user is None


@pytest.mark.anyio
async def test_unit_of_work_rejects_repository_access_when_inactive() -> None:
    uow = SQLAlchemyUnitOfWork(
        _session_factory=cast(SQLAlchemySessionFactory, FakeSessionFactory(session=FakeSession())),
    )

    with pytest.raises(RuntimeError, match="not active"):
        _ = uow.user_repository


@pytest.mark.anyio
async def test_unit_of_work_rejects_exit_when_inactive() -> None:
    uow = SQLAlchemyUnitOfWork(
        _session_factory=cast(SQLAlchemySessionFactory, FakeSessionFactory(session=FakeSession())),
    )

    with pytest.raises(RuntimeError, match="not active"):
        await uow.__aexit__(None, None, None)


@pytest.mark.anyio
async def test_unit_of_work_rejects_nested_scope() -> None:
    uow = SQLAlchemyUnitOfWork(
        _session_factory=cast(
            SQLAlchemySessionFactory,
            FakeSessionFactory(session=PassingSession()),
        ),
    )

    async with uow:
        with pytest.raises(RuntimeError, match="Nested UnitOfWork scopes"):
            async with uow:
                pass


@pytest.mark.anyio
async def test_unit_of_work_closes_scope_when_commit_fails() -> None:
    session = FakeSession()
    uow = SQLAlchemyUnitOfWork(
        _session_factory=cast(SQLAlchemySessionFactory, FakeSessionFactory(session=session)),
    )

    await uow.__aenter__()
    with pytest.raises(TransactionFailureError):
        await uow.__aexit__(None, None, None)

    assert session.closed is True
    with pytest.raises(RuntimeError, match="not active"):
        _ = uow.user_repository


async def _create_user_then_fail(*, uow: UnitOfWork, data: PersistUserDTO) -> None:
    async with uow as active_uow:
        await active_uow.user_repository.create(
            data=data,
            password_hash=_stored_secret_hash(),
        )
        raise TransactionFailureError


def _persist_user_dto(*, username: str) -> PersistUserDTO:
    return PersistUserDTO(
        username=username,
        email=f"{username}@example.com",
        first_name="Test",
        last_name="User",
        password=_VALID_TEST_PASSWORD,
    )


def _stored_secret_hash() -> str:
    return "hash"
