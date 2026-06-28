from abc import ABC, abstractmethod
from typing import Any


class BaseUseCase(ABC):
    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> Any: ...
