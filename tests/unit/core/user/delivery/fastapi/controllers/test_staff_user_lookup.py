from typing import cast

import pytest
from fastapi import HTTPException

from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth_factory import (
    JWTAuthFactory,
)
from fastapi_template.core.user.delivery.fastapi.controllers.staff_user_lookup import (
    StaffUserLookupController,
)
from fastapi_template.core.user.use_cases.get_user_by_id import GetUserByIdUseCase


class MissingUserUseCase:
    async def execute(self, *, user_id: int) -> None:
        return None


@pytest.mark.anyio
async def test_staff_user_lookup_controller_returns_not_found_for_missing_user() -> None:
    controller = _build_controller(
        get_user_by_id_use_case=cast(GetUserByIdUseCase, MissingUserUseCase()),
    )

    with pytest.raises(HTTPException) as exc_info:
        await controller.get_user_by_id(user_id=1)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


def _build_controller(
    *,
    get_user_by_id_use_case: GetUserByIdUseCase | None = None,
) -> StaffUserLookupController:
    return StaffUserLookupController(
        _jwt_auth_factory=cast(JWTAuthFactory, lambda **_kwargs: object()),
        _get_user_by_id_use_case=get_user_by_id_use_case or cast(GetUserByIdUseCase, object()),
    )
