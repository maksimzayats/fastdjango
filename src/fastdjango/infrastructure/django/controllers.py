from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from inspect import iscoroutinefunction
from typing import Any

from fastdjango.foundation.delivery.controllers import BaseController
from fastdjango.infrastructure.django.traced_atomic import traced_atomic


@dataclass(kw_only=True)
class BaseTransactionController(BaseController, ABC):
    def _wrap_route(self, method: Callable[..., Any]) -> Callable[..., Any]:
        method = self._add_transaction(method)
        return super()._wrap_route(method)

    def _add_transaction(self, method: Callable[..., Any]) -> Callable[..., Any]:
        method_name = getattr(method, "__name__", type(method).__name__)

        if iscoroutinefunction(method):
            msg = f"Async route '{method_name}' cannot use BaseTransactionController."
            raise TypeError(msg)

        @wraps(method)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with traced_atomic(
                "controller transaction",
                controller=type(self).__name__,
                method=method_name,
            ):
                return method(*args, **kwargs)

        return wrapper
