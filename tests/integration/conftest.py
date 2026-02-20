import pytest
from diwire import Container
from throttled.asyncio import MemoryStore

from infrastructure.frameworks.throttled.throttler import AsyncThrottlerStoreFactory
from ioc.container import ContainerFactory
from tests.integration.factories import (
    TestCeleryWorkerFactory,
    TestClientFactory,
    TestTasksRegistryFactory,
    TestUserFactory,
)


@pytest.fixture(scope="function")
def container() -> Container:
    container_factory = ContainerFactory()
    container = container_factory()
    container.add_factory(lambda: MemoryStore(), provides=AsyncThrottlerStoreFactory)

    return container


# region Factories


@pytest.fixture(scope="function")
def test_client_factory(container: Container) -> TestClientFactory:
    return TestClientFactory(container=container)


@pytest.fixture(scope="function")
def user_factory(
    transactional_db: None,
    container: Container,
) -> TestUserFactory:
    return TestUserFactory(container=container)


@pytest.fixture(scope="function")
def celery_worker_factory(container: Container) -> TestCeleryWorkerFactory:
    return TestCeleryWorkerFactory(container=container)


@pytest.fixture(scope="function")
def tasks_registry_factory(container: Container) -> TestTasksRegistryFactory:
    return TestTasksRegistryFactory(container=container)


# endregion Factories
