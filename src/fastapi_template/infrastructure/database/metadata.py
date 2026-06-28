from fastapi_template.core.authentication.infrastructure.persistence.sqlalchemy import (
    models as authentication_models,  # noqa: F401
)
from fastapi_template.core.user.infrastructure.persistence.sqlalchemy import (
    models as user_models,  # noqa: F401
)
from fastapi_template.infrastructure.database.base import Base

target_metadata = Base.metadata
