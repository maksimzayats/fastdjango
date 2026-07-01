from fastapi_template.foundation.dto import BaseDTO


class IssueTokenDTO(BaseDTO):
    """Credential payload used by the token issue workflow."""

    username: str
    password: str
