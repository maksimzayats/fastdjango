from __future__ import annotations

import secrets
from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus
from typing import Any, cast

from diwire import Injected
from fastapi import HTTPException
from fastapi.requests import Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from starlette.datastructures import State

from fastdjango.core.authentication.services.jwt import JWTService
from fastdjango.core.user.models import User
from fastdjango.core.user.use_cases import UserUseCase
from fastdjango.foundation.factories import BaseFactory


class AuthenticationMode(StrEnum):
    JWT_REFRESH_SESSION = "jwt-refresh-session"
    STATIC_API_KEYS = "static-api-keys"
    CUSTOM = "custom"


class AuthenticationSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTHENTICATION_")

    mode: AuthenticationMode = AuthenticationMode.JWT_REFRESH_SESSION


class StaticAPIKeyPrincipal(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    username: str
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    is_staff: bool = False
    is_superuser: bool = False

    @property
    def pk(self) -> int:
        return self.id


class StaticAPIKeyRegistrySettings(BaseSettings):
    model_config = SettingsConfigDict(populate_by_name=True)

    api_keys: dict[str, StaticAPIKeyPrincipal] = Field(
        default_factory=dict,
        validation_alias="STATIC_API_KEYS",
    )

    def get_principal_for_api_key(self, *, api_key: str) -> StaticAPIKeyPrincipal | None:
        for registered_api_key, principal in self.api_keys.items():
            if secrets.compare_digest(api_key, registered_api_key):
                return principal

        return None


class AuthenticatedRequestState(State):
    jwt_payload: dict[str, Any]
    user: User | StaticAPIKeyPrincipal


class AuthenticatedRequest(Request):
    state: AuthenticatedRequestState


@dataclass(kw_only=True)
class AccessAuthFactory(BaseFactory):
    _authentication_settings: Injected[AuthenticationSettings]
    _jwt_auth_factory: Injected[JWTAuthFactory]
    _static_api_key_auth_factory: Injected[StaticAPIKeyAuthFactory]

    def __call__(
        self,
        *,
        require_staff: bool = False,
        require_superuser: bool = False,
    ) -> JWTAuth | StaticAPIKeyAuth | AuthenticationNotConfiguredAuth:
        if self._authentication_settings.mode == AuthenticationMode.JWT_REFRESH_SESSION:
            return self._jwt_auth_factory(
                require_staff=require_staff,
                require_superuser=require_superuser,
            )

        if self._authentication_settings.mode == AuthenticationMode.STATIC_API_KEYS:
            return self._static_api_key_auth_factory(
                require_staff=require_staff,
                require_superuser=require_superuser,
            )

        return AuthenticationNotConfiguredAuth()


@dataclass(kw_only=True)
class JWTAuthFactory(BaseFactory):
    """Factory for creating JWT auth instances with optional permission checks.

    Example:
        factory = container.resolve(JWTAuthFactory)
        basic_auth = factory()  # No permission checks
        staff_auth = factory(require_staff=True)  # Requires is_staff=True
        admin_auth = factory(require_superuser=True)  # Requires is_superuser=True
    """

    _jwt_service: Injected[JWTService]
    _user_use_case: Injected[UserUseCase]

    def __call__(
        self,
        *,
        require_staff: bool = False,
        require_superuser: bool = False,
    ) -> JWTAuth:
        """Create a JWT auth instance.

        Args:
            require_staff: If True, require user.is_staff to be True.
            require_superuser: If True, require user.is_superuser to be True.

        Returns:
            A JWTAuth instance configured with the specified permission checks.
        """
        if require_staff or require_superuser:
            return JWTAuthWithPermissions(
                jwt_service=self._jwt_service,
                user_use_case=self._user_use_case,
                require_staff=require_staff,
                require_superuser=require_superuser,
            )

        return JWTAuth(jwt_service=self._jwt_service, user_use_case=self._user_use_case)


@dataclass(kw_only=True)
class StaticAPIKeyAuthFactory(BaseFactory):
    _settings: Injected[StaticAPIKeyRegistrySettings]

    def __call__(
        self,
        *,
        require_staff: bool = False,
        require_superuser: bool = False,
    ) -> StaticAPIKeyAuth:
        return StaticAPIKeyAuth(
            settings=self._settings,
            require_staff=require_staff,
            require_superuser=require_superuser,
        )


class JWTAuth(HTTPBearer):
    def __init__(
        self,
        jwt_service: JWTService,
        user_use_case: UserUseCase,
    ) -> None:
        super().__init__()
        self._jwt_service = jwt_service
        self._user_use_case = user_use_case

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        credentials = await super().__call__(request)
        if credentials is None:
            return None

        request = cast(AuthenticatedRequest, request)

        payload = self._get_token_payload(token=credentials.credentials)
        request.state.jwt_payload = payload

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token payload missing 'sub' field",
            )

        user = await self._user_use_case.get_active_user_by_id(user_id=user_id)

        if user is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="User not found",
            )

        request.state.user = user

        return credentials

    def _get_token_payload(self, token: str) -> dict[str, Any]:
        try:
            return self._jwt_service.decode_token(token=token)
        except self._jwt_service.EXPIRED_SIGNATURE_ERROR as e:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Token has expired",
            ) from e
        except self._jwt_service.INVALID_TOKEN_ERROR as e:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid token",
            ) from e


class StaticAPIKeyAuth(APIKeyHeader):
    def __init__(
        self,
        settings: StaticAPIKeyRegistrySettings,
        *,
        require_staff: bool = False,
        require_superuser: bool = False,
    ) -> None:
        super().__init__(name="X-API-Key", auto_error=False)
        self._settings = settings
        self._require_staff = require_staff
        self._require_superuser = require_superuser

    async def __call__(self, request: Request) -> str | None:
        api_key = await super().__call__(request)
        if api_key is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="API key is required",
            )

        principal = self._settings.get_principal_for_api_key(api_key=api_key)
        if principal is None:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Invalid API key",
            )

        self._check_permissions(principal=principal)
        request = cast(AuthenticatedRequest, request)
        request.state.user = principal

        return api_key

    def _check_permissions(self, *, principal: StaticAPIKeyPrincipal) -> None:
        if self._require_staff and not principal.is_staff:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Staff access required",
            )

        if self._require_superuser and not principal.is_superuser:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Superuser access required",
            )


class AuthenticationNotConfiguredAuth(HTTPBearer):
    def __init__(self) -> None:
        super().__init__(auto_error=False)

    async def __call__(self, _request: Request) -> HTTPAuthorizationCredentials | None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_IMPLEMENTED,
            detail="Authentication is not configured",
        )


class JWTAuthWithPermissions(JWTAuth):
    """JWT auth with optional is_staff/is_superuser checks."""

    def __init__(
        self,
        jwt_service: JWTService,
        user_use_case: UserUseCase,
        *,
        require_staff: bool = False,
        require_superuser: bool = False,
    ) -> None:
        super().__init__(jwt_service=jwt_service, user_use_case=user_use_case)
        self._require_staff = require_staff
        self._require_superuser = require_superuser

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        credentials = await super().__call__(request)

        request = cast(AuthenticatedRequest, request)
        user = request.state.user

        if self._require_staff and not getattr(user, "is_staff", False):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Staff access required",
            )

        if self._require_superuser and not getattr(user, "is_superuser", False):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail="Superuser access required",
            )

        return credentials
