from fastapi.requests import Request

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request_state import (
    AuthenticatedRequestState,
)


class AuthenticatedRequest(Request):
    """FastAPI request variant with authentication state populated by JWT auth."""

    state: AuthenticatedRequestState
