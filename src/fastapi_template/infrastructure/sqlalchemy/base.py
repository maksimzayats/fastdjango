from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

_NAMING_CONVENTION_ITEMS = (
    ("ix", "ix_%(column_0_label)s"),
    ("uq", "uq_%(table_name)s_%(column_0_name)s"),
    ("ck", "ck_%(table_name)s_%(constraint_name)s"),
    ("fk", "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"),
    ("pk", "pk_%(table_name)s"),
)


class Base(DeclarativeBase):
    """Declarative base used by all SQLAlchemy table mappings."""

    metadata = MetaData(naming_convention=dict(_NAMING_CONVENTION_ITEMS))
