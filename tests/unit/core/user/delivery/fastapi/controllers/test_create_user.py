from http import HTTPStatus
from typing import cast

import pytest
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from fastapi_template.core.shared.delivery.fastapi.throttling.ip_throttler_factory import (
    IPThrottlerFactory,
)
from fastapi_template.core.user.delivery.fastapi.controllers.create_user import (
    CreateUserController,
)
from fastapi_template.core.user.delivery.fastapi.schemas.create_user_request import (
    CreateUserRequestSchema,
)
from fastapi_template.core.user.dtos.create_user import CreateUserDTO
from fastapi_template.core.user.entities.user import User
from fastapi_template.core.user.exceptions.user_already_exists import UserAlreadyExistsError
from fastapi_template.core.user.exceptions.weak_password import WeakPasswordError
from fastapi_template.core.user.use_cases.create_user import CreateUserUseCase

_VALID_PASSWORD = "S3cure-test-value-123!"  # noqa: S105
_PASSWORD_HASH = "hash"  # noqa: S105


class RecordingCreateUserUseCase:
    data: CreateUserDTO | None = None

    async def execute(self, *, data: CreateUserDTO) -> User:
        self.data = data
        return _user()


@pytest.mark.anyio
async def test_create_user_controller_maps_create_schema_to_dto() -> None:
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
async def test_create_user_controller_translates_domain_errors(
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
async def test_create_user_controller_reraises_unhandled_errors() -> None:
    controller = _build_controller()
    error = RuntimeError("unexpected")

    with pytest.raises(RuntimeError) as exc_info:
        await controller.handle_exception(error)

    assert exc_info.value is error


def test_create_user_controller_applies_ip_throttle_before_use_case() -> None:
    create_user_use_case = RecordingCreateUserUseCase()
    controller = CreateUserController(
        _ip_throttler_factory=cast(IPThrottlerFactory, RejectingIPThrottlerFactory()),
        _create_user_use_case=cast(CreateUserUseCase, create_user_use_case),
    )
    app = FastAPI()
    router = APIRouter()
    controller.register(router)
    app.include_router(router)

    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/users",
            json={
                "username": "created",
                "email": "created@example.com",
                "first_name": "Created",
                "last_name": "User",
                "password": _VALID_PASSWORD,
            },
        )

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert create_user_use_case.data is None


class RejectingIPThrottlerFactory:
    def __call__(self, *, quota: object) -> object:
        return self.throttle

    async def throttle(self, request: Request) -> None:
        raise HTTPException(
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            detail="Too many requests",
        )


def _build_controller(
    *,
    create_user_use_case: CreateUserUseCase | None = None,
) -> CreateUserController:
    return CreateUserController(
        _ip_throttler_factory=cast(IPThrottlerFactory, object()),
        _create_user_use_case=create_user_use_case or cast(CreateUserUseCase, object()),
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
