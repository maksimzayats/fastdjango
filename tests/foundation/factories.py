from abc import ABC, abstractmethod
from typing import Any

from diwire import Container

from fastdjango.foundation.factories import BaseFactory


class BaseTestFactory(BaseFactory, ABC):
    __test__ = False

    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        pass


class ContainerBasedFactory(BaseTestFactory, ABC):
    def __init__(
        self,
        container: Container,
    ) -> None:
        self._container = container
