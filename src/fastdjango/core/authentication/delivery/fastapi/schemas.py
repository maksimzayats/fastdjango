from pydantic import BaseModel


class IssueTokenRequestSchema(BaseModel):
    username: str
    password: str


class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
