from fastapi_template.foundation.dto import BaseDTO


class RefreshTokenDTO(BaseDTO):
    """Refresh-token payload passed between delivery and core workflows."""

    refresh_token: str
