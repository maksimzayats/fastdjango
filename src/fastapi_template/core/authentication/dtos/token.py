from fastapi_template.foundation.dto import BaseDTO


class TokenDTO(BaseDTO):
    """Define TokenDTO."""

    access_token: str
    refresh_token: str
