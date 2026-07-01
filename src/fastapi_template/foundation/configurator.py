from abc import ABC, abstractmethod


class BaseConfigurator(ABC):
    """Contract for bootstrap components that apply process-wide settings."""

    @abstractmethod
    def configure(self) -> None:
        """Apply side-effectful configuration during application bootstrap."""
        raise NotImplementedError
