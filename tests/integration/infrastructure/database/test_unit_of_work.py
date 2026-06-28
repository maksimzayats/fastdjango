import pytest
from diwire import Container

from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.dtos import CreateUserDTO

_VALID_TEST_PASSWORD = "S3cure-test-password-123!"  # noqa: S105


class TransactionFailureError(Exception):
    pass


@pytest.mark.anyio
async def test_unit_of_work_commits_repository_changes(container: Container) -> None:
    uow = container.resolve(UnitOfWork)
    create_user_data = _create_user_dto(username="committed_user")

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
    create_user_data = _create_user_dto(username="rolled_back_user")

    with pytest.raises(TransactionFailureError):
        await _create_user_then_fail(uow=uow, data=create_user_data)

    async with uow as active_uow:
        persisted_user = await active_uow.user_repository.get_by_username(
            username=create_user_data.username,
        )

    assert persisted_user is None


async def _create_user_then_fail(*, uow: UnitOfWork, data: CreateUserDTO) -> None:
    async with uow as active_uow:
        await active_uow.user_repository.create(
            data=data,
            password_hash=_stored_secret_hash(),
        )
        raise TransactionFailureError


def _create_user_dto(*, username: str) -> CreateUserDTO:
    return CreateUserDTO(
        username=username,
        email=f"{username}@example.com",
        first_name="Test",
        last_name="User",
        password=_VALID_TEST_PASSWORD,
    )


def _stored_secret_hash() -> str:
    return "hash"
