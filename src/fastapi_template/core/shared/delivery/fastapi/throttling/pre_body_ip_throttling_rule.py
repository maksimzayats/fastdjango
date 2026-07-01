from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from starlette.requests import Request

type PreBodyIPThrottler = Callable[[Request], Awaitable[None]]


@dataclass(frozen=True, kw_only=True, slots=True)
class PreBodyIPThrottlingRule:
    """Route-specific pre-body IP throttling rule."""

    method: str
    path: str
    throttler: PreBodyIPThrottler
