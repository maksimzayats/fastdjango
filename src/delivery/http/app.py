from importlib import import_module
from typing import TYPE_CHECKING, cast

from ioc.container import ContainerFactory

if TYPE_CHECKING:
    from delivery.http.factories import FastAPIFactory

_container_factory = ContainerFactory()
_container = _container_factory()

_fastapi_factory_type = cast(
    "type[FastAPIFactory]",
    import_module("delivery.http.factories").FastAPIFactory,
)
_api_factory = _container.resolve(_fastapi_factory_type)

app = _api_factory(include_django=True)
