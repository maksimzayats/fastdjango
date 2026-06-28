from abc import ABC, abstractmethod

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class HealthRepository(ABC):
    @abstractmethod
    async def check_database(self) -> None: ...


class SQLAlchemyHealthRepository(HealthRepository):
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def check_database(self) -> None:
        await self._session.execute(text("SELECT 1"))
