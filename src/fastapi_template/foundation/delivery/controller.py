from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from inspect import getmembers, isclass, iscoroutinefunction
from typing import Any


@dataclass(kw_only=True)
class BaseAsyncController(ABC):
    """Base controller that wraps async endpoints with exception translation."""

    def __post_init__(self) -> None:
        """Wrap public endpoint methods after dataclass initialization."""
        self._wrap_methods()

    @abstractmethod
    def register(self, registry: Any) -> None:
        """Register routes on the delivery registry."""
        raise NotImplementedError

    async def handle_exception(self, exception: Exception) -> Any:
        """Translate a domain exception or re-raise it by default."""
        raise exception

    def _wrap_methods(self) -> None:
        for attr_name, attr in getmembers(self):
            if (
                callable(attr)
                and not isclass(attr)
                and not hasattr(BaseAsyncController, attr_name)
                and not attr_name.startswith("_")
            ):
                setattr(self, attr_name, self._wrap_route(attr))

    def _wrap_route(self, method: Callable[..., Any]) -> Callable[..., Any]:
        return self._add_exception_handler(method)

    def _add_exception_handler(self, method: Callable[..., Any]) -> Callable[..., Any]:
        if not iscoroutinefunction(method):
            method_name = getattr(method, "__name__", type(method).__name__)
            msg = f"Controller endpoint '{method_name}' must be async def."
            raise TypeError(msg)

        @wraps(method)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Invoke an endpoint and delegate exception handling.

            Returns:
                The wrapped endpoint result.
            """
            try:
                return await method(*args, **kwargs)
            except Exception as exception:  # noqa: BLE001
                return await self.handle_exception(exception)

        return wrapper
