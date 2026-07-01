from abc import ABC, abstractmethod
from typing import Any


class BaseUseCase(ABC):
    """Base contract for application actions exposed through ``execute``."""

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Public contract for one application action.

        Returns:
            The use-case result.
        """
        raise NotImplementedError
