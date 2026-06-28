from dataclasses import dataclass, field
from http import HTTPStatus

from diwire import Injected
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request import (
    AuthenticatedRequest,
)
from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth_factory import (
    JWTAuthFactory,
)
from fastapi_template.core.user.delivery.fastapi.schemas.user import UserSchema
from fastapi_template.core.user.use_cases.staff_user_lookup import StaffUserLookupUseCase
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class StaffUserLookupController(BaseAsyncController):
    """Define StaffUserLookupController."""

    _jwt_auth_factory: Injected[JWTAuthFactory]
    _staff_user_lookup_use_case: Injected[StaffUserLookupUseCase]

    _staff_jwt_auth: HTTPBearer = field(init=False)

    def __post_init__(self) -> None:
        """Run post init."""
        self._staff_jwt_auth = self._jwt_auth_factory()
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        """Run register."""
        registry.add_api_route(
            path="/api/v1/users/{user_id}",
            endpoint=self.staff_user_lookup,
            methods=["GET"],
            dependencies=[Depends(self._staff_jwt_auth)],
            response_model=UserSchema,
        )

    async def staff_user_lookup(
        self,
        request: AuthenticatedRequest,
        user_id: int,
    ) -> UserSchema:
        """Run staff user lookup.

        Returns:
        The operation result.
        """
        user = await self._staff_user_lookup_use_case.execute(
            user_id=user_id,
            actor_user_id=request.state.user_id,
        )
        if user is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="User not found",
            )

        return UserSchema.model_validate(user, from_attributes=True)

    async def handle_exception(self, exception: Exception) -> object:
        """Run handle exception.

        Returns:
        The operation result.
        """
        if isinstance(exception, StaffUserLookupUseCase.AUTHENTICATED_USER_NOT_FOUND_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="User not found",
            ) from exception

        if isinstance(exception, StaffUserLookupUseCase.PERMISSION_DENIED_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Permission denied",
            ) from exception

        return await super().handle_exception(exception)
