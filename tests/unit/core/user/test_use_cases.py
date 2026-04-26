import pytest

from fastdjango.core.user.dtos import CreateUserDTO
from fastdjango.core.user.use_cases import UserUseCase

_TEST_PASSWORD = "test-password"  # noqa: S105


def test_create_user_rejects_weak_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_case = UserUseCase()

    def is_valid_password(*, data: CreateUserDTO) -> bool:
        return False

    monkeypatch.setattr(use_case, "is_valid_password", is_valid_password)

    with pytest.raises(UserUseCase.WEAK_PASSWORD_ERROR):
        use_case.create_user(data=_create_user_dto())


def test_create_user_rejects_existing_username_or_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_case = UserUseCase()

    def is_valid_password(*, data: CreateUserDTO) -> bool:
        return True

    def get_user_by_username_or_email(*, username: str, email: str) -> object:
        return object()

    monkeypatch.setattr(use_case, "is_valid_password", is_valid_password)
    monkeypatch.setattr(
        use_case,
        "get_user_by_username_or_email",
        get_user_by_username_or_email,
    )

    with pytest.raises(UserUseCase.USER_ALREADY_EXISTS_ERROR):
        use_case.create_user(data=_create_user_dto())


def _create_user_dto() -> CreateUserDTO:
    return CreateUserDTO(
        username="new_user",
        email="new_user@example.com",
        first_name="New",
        last_name="User",
        password=_TEST_PASSWORD,
    )
