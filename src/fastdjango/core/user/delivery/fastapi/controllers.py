from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from fastdjango.core.authentication.delivery.fastapi.auth import (
    AuthenticatedRequest,
    JWTAuthFactory,
)
from fastdjango.core.user.delivery.fastapi.schemas import (
    CreateUserRequestSchema,
    UserSchema,
)
from fastdjango.core.user.use_cases import UserUseCase
from fastdjango.infrastructure.django.controllers import BaseTransactionController


@dataclass(kw_only=True)
class UserController(BaseTransactionController):
    _jwt_auth_factory: JWTAuthFactory
    _user_use_case: UserUseCase

    def __post_init__(self) -> None:
        self._jwt_auth = self._jwt_auth_factory()
        self._staff_jwt_auth = self._jwt_auth_factory(require_staff=True)
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        registry.add_api_route(
            path="/v1/users/",
            endpoint=self.create_user,
            methods=["POST"],
            response_model=UserSchema,
        )

        registry.add_api_route(
            path="/v1/users/me",
            endpoint=self.get_current_user,
            methods=["GET"],
            dependencies=[Depends(self._jwt_auth)],
            response_model=UserSchema,
        )

        registry.add_api_route(
            path="/v1/users/{user_id}",
            endpoint=self.get_user_by_id,
            methods=["GET"],
            dependencies=[Depends(self._staff_jwt_auth)],
            response_model=UserSchema,
        )

    def create_user(self, request_body: CreateUserRequestSchema) -> UserSchema:
        user = self._user_use_case.create_user(data=request_body)

        return UserSchema.model_validate(user, from_attributes=True)

    def get_current_user(self, request: AuthenticatedRequest) -> UserSchema:
        return UserSchema.model_validate(request.state.user, from_attributes=True)

    def get_user_by_id(
        self,
        user_id: int,
    ) -> UserSchema:
        user = self._user_use_case.get_user_by_id(user_id=user_id)
        if user is None:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="User not found",
            )

        return UserSchema.model_validate(user, from_attributes=True)

    def handle_exception(self, exception: Exception) -> Any:
        if isinstance(exception, UserUseCase.WEAK_PASSWORD_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Password does not meet the strength requirements",
            ) from exception

        if isinstance(exception, UserUseCase.USER_ALREADY_EXISTS_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="A user with the given username or email already exists",
            ) from exception

        return super().handle_exception(exception)
