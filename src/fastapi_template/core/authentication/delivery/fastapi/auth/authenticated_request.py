from fastapi.requests import Request

from fastapi_template.core.authentication.delivery.fastapi.auth.authenticated_request_state import (
    AuthenticatedRequestState,
)


class AuthenticatedRequest(Request):
    """Define AuthenticatedRequest."""

    state: AuthenticatedRequestState
