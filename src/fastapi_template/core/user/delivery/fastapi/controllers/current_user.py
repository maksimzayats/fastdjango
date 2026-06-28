from dataclasses import dataclass, field

from diwire import Injected
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request import (
    AuthenticatedRequest,
)
from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth_factory import (
    JWTAuthFactory,
)
from fastapi_template.core.user.delivery.fastapi.schemas.user import UserSchema
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class CurrentUserController(BaseAsyncController):
    """Define CurrentUserController."""

    _jwt_auth_factory: Injected[JWTAuthFactory]

    _jwt_auth: HTTPBearer = field(init=False)

    def __post_init__(self) -> None:
        """Run post init."""
        self._jwt_auth = self._jwt_auth_factory()
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        """Run register."""
        registry.add_api_route(
            path="/api/v1/users/me",
            endpoint=self.get_current_user,
            methods=["GET"],
            dependencies=[Depends(self._jwt_auth)],
            response_model=UserSchema,
        )

    async def get_current_user(self, request: AuthenticatedRequest) -> UserSchema:
        """Run get current user.

        Returns:
        The operation result.
        """
        return UserSchema.model_validate(request.state.user, from_attributes=True)
