from types import SimpleNamespace
from typing import cast

import pytest
from fastapi import HTTPException

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request import (
    AuthenticatedRequest,
)
from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth_factory import (
    JWTAuthFactory,
)
from fastapi_template.core.user.delivery.fastapi.controllers.staff_user_lookup import (
    StaffUserLookupController,
)
from fastapi_template.core.user.use_cases.staff_user_lookup import StaffUserLookupUseCase


class MissingUserUseCase:
    async def execute(self, *, user_id: int, actor_user_id: int) -> None:
        return None


@pytest.mark.anyio
async def test_staff_user_lookup_controller_returns_not_found_for_missing_user() -> None:
    controller = _build_controller(
        staff_user_lookup_use_case=cast(StaffUserLookupUseCase, MissingUserUseCase()),
    )

    with pytest.raises(HTTPException) as exc_info:
        await controller.staff_user_lookup(
            request=cast(AuthenticatedRequest, SimpleNamespace(state=SimpleNamespace(user_id=2))),
            user_id=1,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("exception", "status_code", "detail"),
    [
        (StaffUserLookupUseCase.AUTHENTICATED_USER_NOT_FOUND_ERROR(), 401, "User not found"),
        (StaffUserLookupUseCase.PERMISSION_DENIED_ERROR(), 403, "Permission denied"),
    ],
)
async def test_staff_user_lookup_controller_translates_domain_errors(
    exception: Exception,
    status_code: int,
    detail: str,
) -> None:
    controller = _build_controller()

    with pytest.raises(HTTPException) as exc_info:
        await controller.handle_exception(exception)

    assert exc_info.value.status_code == status_code
    assert exc_info.value.detail == detail
    if status_code == 401:
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


def _build_controller(
    *,
    staff_user_lookup_use_case: StaffUserLookupUseCase | None = None,
) -> StaffUserLookupController:
    return StaffUserLookupController(
        _jwt_auth_factory=cast(JWTAuthFactory, object),
        _staff_user_lookup_use_case=staff_user_lookup_use_case
        or cast(StaffUserLookupUseCase, object()),
    )
