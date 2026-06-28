from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from diwire import Injected
from fastapi import APIRouter, HTTPException

from fastapi_template.core.user.delivery.fastapi.schemas.create_user_request import (
    CreateUserRequestSchema,
)
from fastapi_template.core.user.delivery.fastapi.schemas.user import UserSchema
from fastapi_template.core.user.dtos.create_user import CreateUserDTO
from fastapi_template.core.user.use_cases.create_user import CreateUserUseCase
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class CreateUserController(BaseAsyncController):
    """Define CreateUserController."""

    _create_user_use_case: Injected[CreateUserUseCase]

    def register(self, registry: APIRouter) -> None:
        """Run register."""
        registry.add_api_route(
            path="/api/v1/users/",
            endpoint=self.create_user,
            methods=["POST"],
            response_model=UserSchema,
        )

    async def create_user(self, request_body: CreateUserRequestSchema) -> UserSchema:
        """Run create user.

        Returns:
        The operation result.
        """
        user = await self._create_user_use_case.execute(
            data=CreateUserDTO(
                email=request_body.email,
                username=request_body.username,
                first_name=request_body.first_name,
                last_name=request_body.last_name,
                password=request_body.password,
            ),
        )

        return UserSchema.model_validate(user, from_attributes=True)

    async def handle_exception(self, exception: Exception) -> Any:
        """Run handle exception.

        Returns:
        The operation result.
        """
        if isinstance(exception, CreateUserUseCase.WEAK_PASSWORD_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Password does not meet the strength requirements",
            ) from exception

        if isinstance(exception, CreateUserUseCase.USER_ALREADY_EXISTS_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="A user with the given username or email already exists",
            ) from exception

        return await super().handle_exception(exception)
