from pydantic import SecretStr

from fastapi_template.infrastructure.sqlalchemy.session import DatabaseSettings


def test_database_settings_converts_postgres_urls_to_async_driver() -> None:
    settings = DatabaseSettings(url=SecretStr("postgres://localhost/app"))

    assert settings.async_url == "postgresql+psycopg://localhost/app"


def test_database_settings_converts_postgresql_urls_to_async_driver() -> None:
    settings = DatabaseSettings(url=SecretStr("postgresql://localhost/app"))

    assert settings.async_url == "postgresql+psycopg://localhost/app"


def test_database_settings_converts_sqlite_urls_to_async_driver() -> None:
    settings = DatabaseSettings(url=SecretStr("sqlite:///db.sqlite3"))

    assert settings.async_url == "sqlite+aiosqlite:///db.sqlite3"
