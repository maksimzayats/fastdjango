from dataclasses import dataclass

from diwire import Injected

from fastapi_template.core.authentication.delivery.fastapi.auth.jwt_auth import JWTAuth
from fastapi_template.core.authentication.services.jwt import JWTService
from fastapi_template.foundation.factory import BaseFactory


@dataclass(kw_only=True)
class JWTAuthFactory(BaseFactory):
    """Factory for auth dependencies that share the configured JWT service."""

    _jwt_service: Injected[JWTService]

    def __call__(self) -> JWTAuth:
        """Create a required bearer-auth dependency for protected routes.

        Returns:
            JWT auth dependency backed by the injected JWT service.
        """
        return JWTAuth(jwt_service=self._jwt_service)
