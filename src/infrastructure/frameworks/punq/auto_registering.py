import logging
from annotationlib import get_annotations
from typing import Any, overload

from punq import Container, Scope
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class AutoRegisteringContainer(Container):  # type: ignore[misc]
    def __init__(
        self,
        settings_scope: Scope = Scope.singleton,
        default_scope: Scope = Scope.singleton,
    ) -> None:
        super().__init__()
        self._settings_scope = settings_scope
        self._default_scope = default_scope

    @overload
    def resolve[T](self, service_key: type[T], **kwargs: Any) -> T: ...
    @overload
    def resolve(self, service_key: Any, **kwargs: Any) -> Any: ...
    def resolve(self, service_key: Any, **kwargs: Any) -> Any:
        self._register_if_missing(service_key)
        return super().resolve(service_key, **kwargs)

    def _register_if_missing(self, service_key: Any) -> None:
        registrations = self.registrations[service_key]
        if registrations:
            return

        if not isinstance(service_key, type):
            msg = f"Cannot auto-register service key {service_key!r} which is not a class."
            raise TypeError(msg)

        if issubclass(service_key, BaseSettings):
            self.register(service_key, factory=lambda: service_key(), scope=self._settings_scope)
            logger.debug(
                "Registered settings %s automatically as %s.",
                service_key,
                self._settings_scope.name,
            )
            return

        self.register(service_key, scope=self._default_scope)
        logger.debug(
            "Registered service %s automatically as %s.",
            service_key,
            self._default_scope.name,
        )

        annotations = get_annotations(service_key.__init__)
        for param_name, param_type in annotations.items():
            if param_name == "return":
                continue

            self._register_if_missing(param_type)
