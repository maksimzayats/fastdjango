from fastapi_template.foundation.dto import BaseDTO


class IssueTokenDTO(BaseDTO):
    """Define IssueTokenDTO."""

    username: str
    password: str
