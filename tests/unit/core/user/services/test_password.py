import pytest

from fastapi_template.core.user.dtos.persist_user import PersistUserDTO
from fastapi_template.core.user.services.password import PasswordService, PasswordServiceSettings

_STRONG_PASSWORD = "S3cure-test-password-123!"  # noqa: S105
_IDENTITY_PASSWORD = "new_user"  # noqa: S105


def test_password_service_hashes_and_verifies_password() -> None:
    service = PasswordService(_settings=PasswordServiceSettings())

    password_hash = service.hash_password(password=_STRONG_PASSWORD)

    assert service.verify_password(password=_STRONG_PASSWORD, password_hash=password_hash)


def test_password_service_rejects_identity_matching_password() -> None:
    service = PasswordService(_settings=PasswordServiceSettings())

    data = PersistUserDTO(
        username="new_user",
        email="new_user@example.com",
        first_name="New",
        last_name="User",
        password=_IDENTITY_PASSWORD,
    )

    with pytest.raises(service.WEAK_PASSWORD_ERROR):
        service.validate(data=data)
