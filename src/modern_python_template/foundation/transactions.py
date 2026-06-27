from contextlib import AbstractContextManager
from typing import Any, Protocol


class TransactionFactory(Protocol):
    def __call__(
        self,
        *,
        span_name: str = "database transaction",
        **span_attributes: Any,
    ) -> AbstractContextManager[Any]: ...
