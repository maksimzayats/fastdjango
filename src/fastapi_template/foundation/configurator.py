from abc import ABC, abstractmethod


class BaseConfigurator(ABC):
    """Base class for configurator implementations."""

    @abstractmethod
    def configure(self) -> None:
        """Configure the component."""
        raise NotImplementedError
