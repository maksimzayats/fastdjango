from http import HTTPStatus

import pytest

from fastapi_template.core.user.constants import PASSWORD_MAX_LENGTH, USER_NAME_MAX_LENGTH
from fastapi_template.core.user.delivery.fastapi.schemas.user import UserSchema
from tests.integration.factories import TestClientFactory

_TEST_PASSWORD = "test-password"  # noqa: S105


def test_create_user(test_client_factory: TestClientFactory) -> None:
    with test_client_factory() as test_client:
        response = test_client.post(
            "/api/v1/users/",
            json={
                "username": "test_new_user",
                "email": "new_user@test.com",
                "password": _TEST_PASSWORD,
                "first_name": "Test",
                "last_name": "User",
            },
        )

    response_data = UserSchema.model_validate(response.json())
    assert response.status_code == HTTPStatus.OK
    assert set(response.json()) == {
        "email",
        "first_name",
        "id",
        "is_staff",
        "is_superuser",
        "last_name",
        "username",
    }
    assert response_data.username == "test_new_user"


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("password", "x" * (PASSWORD_MAX_LENGTH + 1)),
        ("username", "x" * (USER_NAME_MAX_LENGTH + 1)),
    ],
)
def test_create_user_rejects_overlong_fields(
    test_client_factory: TestClientFactory,
    field_name: str,
    field_value: str,
) -> None:
    payload = {
        "username": "test_new_user",
        "email": "new_user@test.com",
        "password": _TEST_PASSWORD,
        "first_name": "Test",
        "last_name": "User",
    }
    payload[field_name] = field_value

    with test_client_factory() as test_client:
        response = test_client.post(
            "/api/v1/users/",
            json=payload,
        )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
