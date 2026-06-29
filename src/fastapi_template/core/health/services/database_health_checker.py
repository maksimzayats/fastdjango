from abc import ABC, abstractmethod


class DatabaseHealthChecker(ABC):
    """Port for probing database readiness outside business transactions."""

    @abstractmethod
    async def check_database(self) -> None:
        """Raise when the backing database cannot execute a minimal query."""
        raise NotImplementedError
