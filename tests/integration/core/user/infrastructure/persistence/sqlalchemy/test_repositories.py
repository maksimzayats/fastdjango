import pytest
from diwire import Container

from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.core.user.dtos import CreateUserDTO


@pytest.mark.anyio
async def test_user_repository_returns_none_for_missing_users(container: Container) -> None:
    uow = container.resolve(UnitOfWork)

    async with uow as active_uow:
        assert await active_uow.user_repository.get_by_id(user_id=404) is None
        assert await active_uow.user_repository.get_active_by_id(user_id=404) is None
        assert await active_uow.user_repository.get_by_username(username="missing") is None
        assert (
            await active_uow.user_repository.get_by_username_or_email(
                username="missing",
                email="missing@example.com",
            )
            is None
        )
        assert (
            await active_uow.user_repository.set_access_flags(
                user_id=404,
                is_staff=True,
                is_superuser=True,
            )
            is None
        )


@pytest.mark.anyio
async def test_user_repository_maps_duplicate_create_error(container: Container) -> None:
    uow = container.resolve(UnitOfWork)

    async with uow as active_uow:
        user_data = _create_user_data()
        duplicate_error = active_uow.user_repository.USER_ALREADY_EXISTS_ERROR
        await active_uow.user_repository.create(data=user_data, password_hash=_password_hash())

    with pytest.raises(duplicate_error):
        async with uow as active_uow:
            await active_uow.user_repository.create(
                data=user_data,
                password_hash=_password_hash(),
            )


@pytest.mark.anyio
async def test_user_repository_finds_user_by_username_or_email(container: Container) -> None:
    uow = container.resolve(UnitOfWork)

    async with uow as active_uow:
        user_data = _create_user_data(
            username="lookup_user",
            email="lookup-user@example.com",
        )
        created_user = await active_uow.user_repository.create(
            data=user_data,
            password_hash=_password_hash(),
        )

    async with uow as active_uow:
        found_user = await active_uow.user_repository.get_by_username_or_email(
            username=user_data.username,
            email="missing@example.com",
        )

    assert found_user is not None
    assert found_user.id == created_user.id


@pytest.mark.anyio
async def test_user_repository_duplicate_lookup_accepts_two_matching_rows(
    container: Container,
) -> None:
    uow = container.resolve(UnitOfWork)

    async with uow as active_uow:
        await active_uow.user_repository.create(
            data=_create_user_data(
                username="duplicate_username",
                email="first@example.com",
            ),
            password_hash=_password_hash(),
        )
        await active_uow.user_repository.create(
            data=_create_user_data(
                username="other_username",
                email="duplicate@example.com",
            ),
            password_hash=_password_hash(),
        )

    async with uow as active_uow:
        found_user = await active_uow.user_repository.get_by_username_or_email(
            username="duplicate_username",
            email="duplicate@example.com",
        )

    assert found_user is not None


def _create_user_data(
    *,
    username: str = "repository_user",
    email: str = "repository@example.com",
) -> CreateUserDTO:
    return CreateUserDTO(
        username=username,
        email=email,
        first_name="Repository",
        last_name="User",
        password=_valid_password(),
    )


def _password_hash() -> str:
    return "argon2-hash-value"


def _valid_password() -> str:
    return "S3cure-test-value-123!"
