from dataclasses import dataclass, field

from diwire import Injected
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from fastapi_template.foundation.factory import BaseFactory


class DatabaseSettings(BaseSettings):
    """Database connection settings for async SQLAlchemy."""

    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: SecretStr = SecretStr("sqlite+aiosqlite:///db.sqlite3")
    echo: bool = False

    @property
    def async_url(self) -> str:
        """Convert common database URLs to async SQLAlchemy driver URLs.

        Returns:
            Database URL using an async-compatible driver.
        """
        raw_url = self.url.get_secret_value()
        if raw_url.startswith("postgres://"):
            return raw_url.replace("postgres://", "postgresql+psycopg://", 1)

        if raw_url.startswith("postgresql://"):
            return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)

        if raw_url.startswith("sqlite:///"):
            return raw_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

        return raw_url


@dataclass(kw_only=True)
class SQLAlchemySessionFactory(BaseFactory):
    """Lazy async SQLAlchemy engine and session factory."""

    _database_settings: Injected[DatabaseSettings]

    _engine: AsyncEngine | None = field(default=None, init=False)
    _session_factory: async_sessionmaker[AsyncSession] | None = field(default=None, init=False)

    def __call__(self) -> AsyncSession:
        """Create an async session from the cached session factory.

        Returns:
            A new SQLAlchemy async session.
        """
        if self._session_factory is None:
            self._engine = create_async_engine(
                self._database_settings.async_url,
                echo=self._database_settings.echo,
                pool_pre_ping=True,
            )
            self._session_factory = async_sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
            )

        return self._session_factory()

    async def dispose(self) -> None:
        """Dispose the cached SQLAlchemy engine."""
        if self._engine is None:
            return

        await self._engine.dispose()
        self._engine = None
        self._session_factory = None
