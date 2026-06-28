import pytest

from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.services.permission import UserPermissionService

_PASSWORD_HASH = "argon2-hash-value"  # noqa: S105


def test_permission_service_rejects_missing_staff_access() -> None:
    service = UserPermissionService()

    with pytest.raises(service.PERMISSION_DENIED_ERROR):
        service.check_access(
            user=_build_user(is_staff=False),
            require_staff=True,
            require_superuser=False,
        )


def test_permission_service_rejects_missing_superuser_access() -> None:
    service = UserPermissionService()

    with pytest.raises(service.PERMISSION_DENIED_ERROR):
        service.check_access(
            user=_build_user(is_superuser=False),
            require_staff=False,
            require_superuser=True,
        )


def _build_user(
    *,
    is_staff: bool = True,
    is_superuser: bool = True,
) -> User:
    return User(
        id=1,
        username="test_user",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=_PASSWORD_HASH,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
