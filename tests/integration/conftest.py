import os
from collections.abc import Iterator
from functools import partial
from pathlib import Path
from urllib.parse import urlparse

import anyio
import pytest
from alembic import command
from alembic.config import Config
from diwire import Container
from throttled.asyncio import MemoryStore

from fastapi_template.infrastructure.sqlalchemy.session import SQLAlchemySessionFactory
from fastapi_template.infrastructure.throttled.async_store_factory import (
    AsyncThrottlerStoreFactory,
)
from fastapi_template.ioc.container import get_container
from tests.integration.factories import (
    TestClientFactory,
    TestRefreshSessionFactory,
    TestUserFactory,
)


@pytest.fixture(scope="function")
def container(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Container]:
    if integration_database_url := os.environ.get("INTEGRATION_DATABASE_URL"):
        validate_integration_database_url(database_url=integration_database_url)
        monkeypatch.setenv("DATABASE_URL", integration_database_url)
        _reset_database()
    else:
        database_path = tmp_path / "test.sqlite3"
        monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{database_path}")

    _run_migrations()

    resolved_container = get_container(configure_logfire=False, instrument_libraries=False)
    session_factory = resolved_container.resolve(SQLAlchemySessionFactory)
    resolved_container.add_instance(session_factory, provides=SQLAlchemySessionFactory)
    resolved_container.add_instance(
        lambda: MemoryStore(),  # noqa: PLW0108
        provides=AsyncThrottlerStoreFactory,
    )

    yield resolved_container

    anyio.run(partial(_dispose_database_engine, session_factory=session_factory))


@pytest.fixture(scope="function")
def test_client_factory(container: Container) -> TestClientFactory:
    return TestClientFactory(container=container)


@pytest.fixture(scope="function")
def user_factory(container: Container) -> TestUserFactory:
    return TestUserFactory(container=container)


@pytest.fixture(scope="function")
def refresh_session_factory(container: Container) -> TestRefreshSessionFactory:
    return TestRefreshSessionFactory(container=container)


def _run_migrations() -> None:
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")


def _reset_database() -> None:
    alembic_config = Config("alembic.ini")
    command.downgrade(alembic_config, "base")


def validate_integration_database_url(*, database_url: str) -> None:
    """Reject integration database URLs that are unsafe to reset."""
    if not database_url.startswith(("postgres://", "postgresql://")):
        pytest.fail("INTEGRATION_DATABASE_URL must be a PostgreSQL URL")

    database_name = urlparse(database_url).path.strip("/")
    if database_name.startswith("test_") or database_name.endswith("_test"):
        return

    pytest.fail(
        "INTEGRATION_DATABASE_URL database name must start with test_ or end with _test",
    )


async def _dispose_database_engine(*, session_factory: SQLAlchemySessionFactory) -> None:
    await session_factory.dispose()
