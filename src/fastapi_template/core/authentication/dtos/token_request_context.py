from fastapi_template.foundation.dto import BaseDTO


class TokenRequestContextDTO(BaseDTO):
    """Define TokenRequestContextDTO."""

    user_agent: str
    ip_address_trace: str | None
