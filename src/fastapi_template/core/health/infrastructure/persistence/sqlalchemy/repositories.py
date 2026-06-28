from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi_template.core.health.repositories import HealthRepository


class SQLAlchemyHealthRepository(HealthRepository):
    """Define SQLAlchemyHealthRepository."""

    def __init__(self, *, session: AsyncSession) -> None:
        """Initialize the instance."""
        self._session = session

    async def check_database(self) -> None:
        """Check database readiness."""
        await self._session.execute(text("SELECT 1"))
