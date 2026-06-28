from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from diwire import Container
from throttled.asyncio import MemoryStore

from fastapi_template.infrastructure.throttled.throttler import AsyncThrottlerStoreFactory
from fastapi_template.ioc.container import get_container
from tests.integration.factories import TestClientFactory, TestUserFactory


@pytest.fixture(scope="function")
def container(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Container:
    database_path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path}")
    _run_migrations()

    container = get_container(configure_logfire=False, instrument_libraries=False)
    container.add_instance(lambda: MemoryStore(), provides=AsyncThrottlerStoreFactory)  # noqa: PLW0108

    return container


@pytest.fixture(scope="function")
def test_client_factory(container: Container) -> TestClientFactory:
    return TestClientFactory(container=container)


@pytest.fixture(scope="function")
def user_factory(container: Container) -> TestUserFactory:
    return TestUserFactory(container=container)


def _run_migrations() -> None:
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")
