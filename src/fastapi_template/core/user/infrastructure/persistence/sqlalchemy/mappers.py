from fastapi_template.core.user.entities import User
from fastapi_template.core.user.infrastructure.persistence.sqlalchemy.models import UserModel


def user_from_model(*, model: UserModel) -> User:
    """Map a SQLAlchemy user model to a core user entity.

    Returns:
        The mapped core user entity.
    """
    return User(
        id=model.id,
        username=model.username,
        email=model.email,
        first_name=model.first_name,
        last_name=model.last_name,
        password_hash=model.password_hash,
        is_active=model.is_active,
        is_staff=model.is_staff,
        is_superuser=model.is_superuser,
    )
