from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any

from logfire import LogfireSpan

from fastdjango.foundation.factories import BaseFactory
from fastdjango.infrastructure.django.traced_atomic import traced_atomic


@dataclass(kw_only=True)
class DjangoTransactionFactory(BaseFactory):
    def __call__(
        self,
        *,
        span_name: str = "database transaction",
        **span_attributes: Any,
    ) -> AbstractContextManager[LogfireSpan]:
        return traced_atomic(span_name=span_name, **span_attributes)
