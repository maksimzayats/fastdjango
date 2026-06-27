from modern_python_template.entrypoints.celery.factories import CeleryAppFactory
from modern_python_template.entrypoints.celery.registry import TasksRegistry
from modern_python_template.ioc.container import get_container

_container = get_container()

_app_factory = _container.resolve(CeleryAppFactory)

# Register tasks
_registry = _container.resolve(TasksRegistry)

app = _app_factory()
