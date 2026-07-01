from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, kw_only=True)
class JsonResponse:
    """Describe an HTTP JSON response payload and pagination link."""

    payload: Any
    link: str | None
