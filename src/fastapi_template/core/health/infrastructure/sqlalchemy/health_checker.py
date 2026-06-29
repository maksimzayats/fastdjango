from dataclasses import dataclass

from diwire import Injected
from sqlalchemy import text

from fastapi_template.core.health.services.database_health_checker import (
    DatabaseHealthChecker,
)
from fastapi_template.infrastructure.sqlalchemy.session import SQLAlchemySessionFactory


@dataclass(kw_only=True)
class SQLAlchemyDatabaseHealthChecker(DatabaseHealthChecker):
    """Database readiness checker backed by a short-lived SQLAlchemy session."""

    _session_factory: Injected[SQLAlchemySessionFactory]

    async def check_database(self) -> None:
        """Execute a minimal query using a dedicated health-check session."""
        async with self._session_factory() as session:
            await session.execute(text("SELECT 1"))
