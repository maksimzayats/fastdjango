from fastapi_template.foundation.dto import BaseDTO


class TokenRequestContextDTO(BaseDTO):
    """Request metadata stored with a newly issued refresh session."""

    user_agent: str
    ip_address_trace: str | None
