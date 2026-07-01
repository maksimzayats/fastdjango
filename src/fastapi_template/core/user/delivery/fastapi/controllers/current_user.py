from dataclasses import dataclass, field

from diwire import Injected
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request import (
    AuthenticatedRequest,
)
from fastapi_template.core.authentication.delivery.fastapi.auth.bearer_authentication_error import (
    bearer_authentication_error,
)
from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth_factory import (
    JWTAuthFactory,
)
from fastapi_template.core.user.delivery.fastapi.schemas.user import UserSchema
from fastapi_template.core.user.use_cases.get_active_user_by_id import (
    GetActiveUserByIdUseCase,
)
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class CurrentUserController(BaseAsyncController):
    """HTTP adapter for returning the active authenticated user."""

    _jwt_auth_factory: Injected[JWTAuthFactory]
    _get_active_user_by_id_use_case: Injected[GetActiveUserByIdUseCase]

    _jwt_auth: HTTPBearer = field(init=False)

    def __post_init__(self) -> None:
        """Build the reusable JWT dependency before route registration."""
        self._jwt_auth = self._jwt_auth_factory()
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        """Attach the current-user endpoint to the FastAPI router."""
        registry.add_api_route(
            path="/api/v1/users/me",
            endpoint=self.get_current_user,
            methods=["GET"],
            dependencies=[Depends(self._jwt_auth)],
            response_model=UserSchema,
        )

    async def get_current_user(self, request: AuthenticatedRequest) -> UserSchema:
        """Load the active user identified by the authenticated request.

        Returns:
            Serialized user data for the authenticated user.
        """
        user = await self._get_active_user_by_id_use_case.execute(
            user_id=request.state.user_id,
        )
        if user is None:
            raise bearer_authentication_error(detail="User not found")

        return UserSchema.model_validate(user, from_attributes=True)
