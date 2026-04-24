from fastdjango.core.shared.delivery.celery.factories import CeleryAppFactory, TasksRegistryFactory
from fastdjango.ioc.container import get_container

_container = get_container()

_registry_factory = _container.resolve(TasksRegistryFactory)
_app_factory = _container.resolve(CeleryAppFactory)

# Register tasks
_registry = _registry_factory()

app = _app_factory()
