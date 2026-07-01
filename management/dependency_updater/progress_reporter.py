import itertools
import sys
import threading
from types import TracebackType
from typing import Self

from management.dependency_updater.output import _write_line

_SPINNER_CLEAR_EXTRA_WIDTH = 8
_SPINNER_INTERVAL_SECONDS = 0.1


class ProgressReporter:
    """Report dependency updater progress to standard output."""

    def __init__(self, *, enabled: bool = True) -> None:
        """Store whether progress messages should be emitted."""
        self._enabled = enabled

    def step(self, message: str, *, spinner: bool = True) -> _ProgressStep:
        """Create a context manager that reports one updater step.

        Args:
            message: Progress message to show.
            spinner: Whether TTY output should use a spinner.

        Returns:
            A progress step context manager.
        """
        return _ProgressStep(
            message=message,
            enabled=self._enabled,
            spinner=spinner,
        )


class _ProgressStep:
    def __init__(self, *, message: str, enabled: bool, spinner: bool) -> None:
        self._message = message
        self._enabled = enabled
        self._spinner = spinner
        self._stop_event: threading.Event | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> Self:
        if not self._enabled:
            return self

        if self._use_spinner:
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
            return self

        _write_line(f"{self._message}...")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        if not self._enabled:
            return

        if self._thread is not None and self._stop_event is not None:
            self._stop_event.set()
            self._thread.join()
            clear_width = len(self._message) + _SPINNER_CLEAR_EXTRA_WIDTH
            clear_text = " " * clear_width
            sys.stdout.write(f"\r{clear_text}\r")

        status = "done"
        if exc_type is not None:
            status = "failed"
        _write_line(f"{self._message}: {status}")

    @property
    def _use_spinner(self) -> bool:
        return self._spinner and sys.stdout.isatty()

    def _spin(self) -> None:
        stop_event = self._stop_event
        if stop_event is None:
            return

        for frame in itertools.cycle("|/-\\"):
            sys.stdout.write(f"\r{frame} {self._message}...")
            sys.stdout.flush()
            if stop_event.wait(_SPINNER_INTERVAL_SECONDS):
                return
