from typing import Any

from starlette.datastructures import State

from fastapi_template.core.user.entities.user import User


class AuthenticatedRequestState(State):
    """Define AuthenticatedRequestState."""

    jwt_payload: dict[str, Any]
    user: User
