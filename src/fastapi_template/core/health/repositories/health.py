from abc import ABC, abstractmethod


class HealthRepository(ABC):
    """Define HealthRepository."""

    @abstractmethod
    async def check_database(self) -> None:
        """Check database readiness."""
        raise NotImplementedError
