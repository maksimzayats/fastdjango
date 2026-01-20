from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from infrastructure.frameworks.django.settings.pydantic_adapter import PydanticSettingsAdapter


def test_adapt_settings() -> None:
    class Settings1(BaseSettings):
        value1: str = "default1"

    class Settings2(BaseSettings):
        model_config = SettingsConfigDict(alias_generator=lambda name: f"settings2_{name}")

        value2: int = 42

    class Settings3(BaseSettings):
        secret_value: SecretStr = Field(default=SecretStr("secret"), alias="settings3_secret_value")

    adapter = PydanticSettingsAdapter()
    settings_locals: dict[str, object] = {}
    adapter.adapt(
        Settings1(),
        Settings2(),
        Settings3(),
        settings_locals=settings_locals,
    )

    assert settings_locals["VALUE1"] == "default1"
    assert settings_locals["SETTINGS2_VALUE2"] == 42
    assert settings_locals["SETTINGS3_SECRET_VALUE"] == "secret"  # noqa: S105
