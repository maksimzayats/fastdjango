from diwire import Container

from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork


def register_dependencies(container: Container) -> None:
    container.add(SQLAlchemyUnitOfWork, provides=UnitOfWork)
