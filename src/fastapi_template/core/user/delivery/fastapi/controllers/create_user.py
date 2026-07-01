from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from diwire import Injected
from fastapi import APIRouter, HTTPException

from fastapi_template.core.user.delivery.fastapi.schemas.create_user_request import (
    CreateUserRequestSchema,
)
from fastapi_template.core.user.delivery.fastapi.schemas.user import UserSchema
from fastapi_template.core.user.dtos.register_user import RegisterUserDTO
from fastapi_template.core.user.use_cases.register_user import RegisterUserUseCase
from fastapi_template.foundation.delivery.controller import BaseAsyncController


@dataclass(kw_only=True)
class CreateUserController(BaseAsyncController):
    """HTTP adapter for creating users from public registration input."""

    _create_user_use_case: Injected[RegisterUserUseCase]

    def register(self, registry: APIRouter) -> None:
        """Attach the user creation endpoint to the FastAPI router."""
        registry.add_api_route(
            path="/api/v1/users",
            endpoint=self.create_user,
            methods=["POST"],
            response_model=UserSchema,
        )

    async def create_user(self, request_body: CreateUserRequestSchema) -> UserSchema:
        """Map the HTTP request body to the user creation use case.

        Returns:
            Serialized user data for the created account.
        """
        user = await self._create_user_use_case.execute(
            data=RegisterUserDTO(
                email=request_body.email,
                username=request_body.username,
                first_name=request_body.first_name,
                last_name=request_body.last_name,
                password=request_body.password,
            ),
        )

        return UserSchema.model_validate(user, from_attributes=True)

    async def handle_exception(self, exception: Exception) -> Any:
        """Translate user creation failures into HTTP responses.

        Returns:
            The delegated handler result for unrecognized exceptions.
        """
        if isinstance(exception, RegisterUserUseCase.WEAK_PASSWORD_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Password does not meet the strength requirements",
            ) from exception

        if isinstance(exception, RegisterUserUseCase.USER_ALREADY_EXISTS_ERROR):
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="A user with the given username or email already exists",
            ) from exception

        return await super().handle_exception(exception)
