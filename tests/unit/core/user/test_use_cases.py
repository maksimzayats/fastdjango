import pytest
from asgiref.sync import sync_to_async
from django.db import IntegrityError

from modern_python_template.core.user.dtos import CreateUserDTO
from modern_python_template.core.user.models import User
from modern_python_template.core.user.use_cases import UserUseCase
from modern_python_template.infrastructure.django.transactions import DjangoTransactionFactory

_STRONG_PASSWORD = "S3cure-test-password-123!"  # noqa: S105
_WEAK_PASSWORD = "123"  # noqa: S105


@pytest.mark.anyio
async def test_create_user_rejects_weak_password() -> None:
    use_case = UserUseCase(_transaction_factory=DjangoTransactionFactory())

    with pytest.raises(UserUseCase.WEAK_PASSWORD_ERROR):
        await use_case.create_user(data=_create_user_dto(password=_WEAK_PASSWORD))


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    ("username", "email"),
    [
        ("existing_user", "new_user@example.com"),
        ("new_user", "existing_user@example.com"),
    ],
)
async def test_create_user_rejects_existing_username_or_email(
    username: str,
    email: str,
) -> None:
    use_case = UserUseCase(_transaction_factory=DjangoTransactionFactory())
    await sync_to_async(
        User.objects.create_user,
        thread_sensitive=True,
    )(
        username="existing_user",
        email="existing_user@example.com",
        password=_STRONG_PASSWORD,
    )

    with pytest.raises(UserUseCase.USER_ALREADY_EXISTS_ERROR):
        await use_case.create_user(
            data=_create_user_dto(
                username=username,
                email=email,
            ),
        )

    user_count = await User.objects.acount()

    assert user_count == 1


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_create_user_maps_integrity_error_to_already_exists_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_case = UserUseCase(_transaction_factory=DjangoTransactionFactory())

    def raise_integrity_error(**kwargs: object) -> None:
        raise IntegrityError

    monkeypatch.setattr(User.objects, "create", raise_integrity_error)

    with pytest.raises(UserUseCase.USER_ALREADY_EXISTS_ERROR):
        await use_case.create_user(data=_create_user_dto())


def _create_user_dto(
    *,
    username: str = "new_user",
    email: str = "new_user@example.com",
    password: str = _STRONG_PASSWORD,
) -> CreateUserDTO:
    return CreateUserDTO(
        username=username,
        email=email,
        first_name="New",
        last_name="User",
        password=password,
    )
