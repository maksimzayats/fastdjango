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

from fastapi_template.foundation.factories import BaseFactory


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: SecretStr = SecretStr("sqlite+aiosqlite:///db.sqlite3")
    echo: bool = False

    @property
    def async_url(self) -> str:
        value = self.url.get_secret_value()
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)

        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)

        if value.startswith("sqlite:///"):
            return value.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

        return value


@dataclass(kw_only=True)
class SQLAlchemySessionFactory(BaseFactory):
    _database_settings: Injected[DatabaseSettings]

    _engine: AsyncEngine | None = field(default=None, init=False)
    _session_factory: async_sessionmaker[AsyncSession] | None = field(default=None, init=False)

    def __call__(self) -> AsyncSession:
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
