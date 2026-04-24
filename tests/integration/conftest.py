import pytest
from diwire import Container
from throttled.asyncio import MemoryStore

from fastdjango.infrastructure.throttled.throttler import AsyncThrottlerStoreFactory
from fastdjango.ioc.container import get_container
from tests.integration.factories import (
    TestCeleryWorkerFactory,
    TestClientFactory,
    TestTasksRegistryFactory,
    TestUserFactory,
)


@pytest.fixture(scope="function")
def container() -> Container:
    container = get_container()
    container.add_instance(lambda: MemoryStore(), provides=AsyncThrottlerStoreFactory)  # noqa: PLW0108

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
