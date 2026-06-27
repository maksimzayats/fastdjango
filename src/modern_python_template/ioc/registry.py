from diwire import Container

from modern_python_template.entrypoints.celery.factories import TasksRegistryFactory
from modern_python_template.entrypoints.celery.registry import TasksRegistry
from modern_python_template.foundation.transactions import TransactionFactory
from modern_python_template.infrastructure.django.transactions import DjangoTransactionFactory


def register_dependencies(container: Container) -> None:
    container.add(DjangoTransactionFactory, provides=TransactionFactory)
    container.add_factory_class(TasksRegistryFactory, provides=TasksRegistry)
