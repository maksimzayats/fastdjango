from typing import cast

import pytest
from fastapi import HTTPException

from fastapi_template.core.authentication.delivery.fastapi.auth import JWTAuthFactory
from fastapi_template.core.user.delivery.fastapi.controllers import UserController
from fastapi_template.core.user.delivery.fastapi.schemas import CreateUserRequestSchema
from fastapi_template.core.user.dtos import CreateUserDTO
from fastapi_template.core.user.entities import User
from fastapi_template.core.user.exceptions import UserAlreadyExistsError, WeakPasswordError
from fastapi_template.core.user.use_cases import CreateUserUseCase, GetUserByIdUseCase

_VALID_PASSWORD = "S3cure-test-value-123!"  # noqa: S105
_PASSWORD_HASH = "hash"  # noqa: S105


class RecordingCreateUserUseCase:
    data: CreateUserDTO | None = None

    async def execute(self, *, data: CreateUserDTO) -> User:
        self.data = data
        return _user()


class MissingUserUseCase:
    async def execute(self, *, user_id: int) -> None:
        return None


@pytest.mark.anyio
async def test_user_controller_maps_create_schema_to_dto() -> None:
    create_user_use_case = RecordingCreateUserUseCase()
    controller = _build_controller(
        create_user_use_case=cast(CreateUserUseCase, create_user_use_case),
    )

    response = await controller.create_user(
        request_body=CreateUserRequestSchema(
            username="created",
            email="created@example.com",
            first_name="Created",
            last_name="User",
            password=_VALID_PASSWORD,
        ),
    )

    assert create_user_use_case.data == CreateUserDTO(
        username="created",
        email="created@example.com",
        first_name="Created",
        last_name="User",
        password=_VALID_PASSWORD,
    )
    assert response.username == "test"


@pytest.mark.anyio
async def test_user_controller_returns_not_found_for_missing_staff_lookup() -> None:
    controller = _build_controller(
        get_user_by_id_use_case=cast(GetUserByIdUseCase, MissingUserUseCase()),
    )

    with pytest.raises(HTTPException) as exc_info:
        await controller.get_user_by_id(user_id=1)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("exception", "status_code", "detail"),
    [
        (WeakPasswordError(), 400, "Password does not meet the strength requirements"),
        (
            UserAlreadyExistsError(),
            409,
            "A user with the given username or email already exists",
        ),
    ],
)
async def test_user_controller_translates_domain_errors(
    exception: Exception,
    status_code: int,
    detail: str,
) -> None:
    controller = _build_controller()

    with pytest.raises(HTTPException) as exc_info:
        await controller.handle_exception(exception)

    assert exc_info.value.status_code == status_code
    assert exc_info.value.detail == detail


@pytest.mark.anyio
async def test_user_controller_reraises_unhandled_errors() -> None:
    controller = _build_controller()
    error = RuntimeError("unexpected")

    with pytest.raises(RuntimeError) as exc_info:
        await controller.handle_exception(error)

    assert exc_info.value is error


def _build_controller(
    *,
    create_user_use_case: CreateUserUseCase | None = None,
    get_user_by_id_use_case: GetUserByIdUseCase | None = None,
) -> UserController:
    return UserController(
        _jwt_auth_factory=cast(JWTAuthFactory, lambda **_kwargs: object()),
        _create_user_use_case=create_user_use_case or cast(CreateUserUseCase, object()),
        _get_user_by_id_use_case=get_user_by_id_use_case or cast(GetUserByIdUseCase, object()),
    )


def _user() -> User:
    return User(
        id=1,
        username="test",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        password_hash=_PASSWORD_HASH,
    )
