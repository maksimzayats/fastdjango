from dataclasses import dataclass, field
from http import HTTPStatus

from diwire import Injected
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer

from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth_factory import (
    JWTAuthFactory,
)
from fastapi_template.core.user.delivery.fastapi.schemas.user import UserSchema
from fastapi_template.core.user.use_cases.get_user_by_id import GetUserByIdUseCase
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class StaffUserLookupController(BaseAsyncController):
    """Define StaffUserLookupController."""

    _jwt_auth_factory: Injected[JWTAuthFactory]
    _get_user_by_id_use_case: Injected[GetUserByIdUseCase]

    _staff_jwt_auth: HTTPBearer = field(init=False)

    def __post_init__(self) -> None:
        """Run post init."""
        self._staff_jwt_auth = self._jwt_auth_factory(require_staff=True)
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        """Run register."""
        registry.add_api_route(
            path="/api/v1/users/{user_id}",
            endpoint=self.get_user_by_id,
            methods=["GET"],
            dependencies=[Depends(self._staff_jwt_auth)],
            response_model=UserSchema,
        )

    async def get_user_by_id(
        self,
        user_id: int,
    ) -> UserSchema:
        """Run get user by id.

        Returns:
        The operation result.
        """
        user = await self._get_user_by_id_use_case.execute(user_id=user_id)
        if user is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="User not found",
            )

        return UserSchema.model_validate(user, from_attributes=True)
