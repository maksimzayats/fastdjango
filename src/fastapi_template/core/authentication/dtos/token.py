from fastapi_template.foundation.dto import BaseDTO


class TokenDTO(BaseDTO):
    """Token pair returned by authentication workflows."""

    access_token: str
    refresh_token: str
