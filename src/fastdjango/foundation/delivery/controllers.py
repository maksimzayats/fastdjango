from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any


@dataclass(kw_only=True)
class BaseController(ABC):
    def __post_init__(self) -> None:
        self._wrap_methods()

    @abstractmethod
    def register(self, registry: Any) -> None: ...

    def handle_exception(self, exception: Exception) -> Any:
        raise exception

    def _wrap_methods(self) -> None:
        for attr_name in dir(self):
            attr = getattr(self, attr_name)

            if (
                callable(attr)
                and not hasattr(BaseController, attr_name)
                and not attr_name.startswith("_")
                and attr_name not in dir(BaseController)
            ):
                setattr(self, attr_name, self._wrap_route(attr))

    def _wrap_route(self, method: Callable[..., Any]) -> Callable[..., Any]:
        return self._add_exception_handler(method)

    def _add_exception_handler(self, method: Callable[..., Any]) -> Callable[..., Any]:
        if iscoroutinefunction(method):
            method_name = getattr(method, "__name__", type(method).__name__)
            msg = f"Async route '{method_name}' must inherit from BaseAsyncController."
            raise TypeError(msg)

        @wraps(method)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return method(*args, **kwargs)
            except Exception as e:  # noqa: BLE001
                return self.handle_exception(e)

        return wrapper


@dataclass(kw_only=True)
class BaseAsyncController(ABC):
    def __post_init__(self) -> None:
        self._wrap_methods()

    @abstractmethod
    def register(self, registry: Any) -> None: ...

    async def handle_exception(self, exception: Exception) -> Any:
        raise exception

    def _wrap_methods(self) -> None:
        for attr_name in dir(self):
            attr = getattr(self, attr_name)

            if (
                callable(attr)
                and not hasattr(BaseAsyncController, attr_name)
                and not attr_name.startswith("_")
                and attr_name not in dir(BaseAsyncController)
            ):
                setattr(self, attr_name, self._wrap_route(attr))

    def _wrap_route(self, method: Callable[..., Any]) -> Callable[..., Any]:
        return self._add_exception_handler(method)

    def _add_exception_handler(self, method: Callable[..., Any]) -> Callable[..., Any]:
        if not iscoroutinefunction(method):
            method_name = getattr(method, "__name__", type(method).__name__)
            msg = f"Sync route '{method_name}' must inherit from BaseController."
            raise TypeError(msg)

        @wraps(method)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await method(*args, **kwargs)
            except Exception as e:  # noqa: BLE001
                return await self.handle_exception(e)

        return wrapper
