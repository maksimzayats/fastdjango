from typing import Any

from starlette.datastructures import State


class AuthenticatedRequestState(State):
    """Request-local authentication values attached after bearer-token validation."""

    jwt_payload: dict[str, Any]
    user_id: int
