from fastapi_template.core.authentication.infrastructure.sqlalchemy.models.refresh_session import (
    RefreshSessionModel,  # noqa: F401
)
from fastapi_template.core.user.infrastructure.sqlalchemy.models.user import (
    UserModel,  # noqa: F401
)
from fastapi_template.infrastructure.sqlalchemy.base import Base

target_metadata = Base.metadata
