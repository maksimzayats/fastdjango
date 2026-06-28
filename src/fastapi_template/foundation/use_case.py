from abc import ABC, abstractmethod
from typing import Any


class BaseUseCase(ABC):
    """Define BaseUseCase."""

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the use case.

        Returns:
            The use-case result.
        """
        raise NotImplementedError
