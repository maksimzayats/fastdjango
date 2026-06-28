from fastapi_template.foundation.dto import BaseDTO


class RefreshTokenDTO(BaseDTO):
    """Define RefreshTokenDTO."""

    refresh_token: str
