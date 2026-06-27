# Settings Reference

Use this file when a service, use case, adapter, client, or entrypoint needs
runtime configuration.

## Contents

- [Rule](#rule)
- [Service Settings](#service-settings)
- [Adapter Settings](#adapter-settings)
- [Container Registration](#container-registration)
- [Test Overrides](#test-overrides)
- [Guidance](#guidance)

## Rule

If a class needs configuration, define a dedicated `pydantic-settings` settings
class backed by environment variables. Put the settings class above the class
that consumes it. Inject the settings object like any other dependency.

For new repos, add `pydantic-settings` as a runtime dependency.

For a settings class dedicated to one consumer, define it in the same module
immediately above the consuming class. If several classes share the same
configuration, place the settings class in the narrowest shared module above
those consumers in the package.

Do not read environment variables directly inside services, use cases, or
adapters.

Construct environment-backed settings at the composition edge by default, then
register or pass the settings instance. Do not rely on hidden auto-creation when
that would make environment loading happen deep in the object graph.

## Service Settings

```python
from dataclasses import dataclass

from diwire import Injected
from pydantic_settings import BaseSettings, SettingsConfigDict


class TokenIssuerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TOKEN_")

    secret_key: str
    ttl_seconds: int = 3600


@dataclass(kw_only=True, slots=True)
class TokenIssuer:
    _settings: Injected[TokenIssuerSettings]

    def issue_token(self, *, user_id: int) -> str:
        return f"{user_id}:{self._settings.ttl_seconds}"
```

Environment variables:

```text
TOKEN_SECRET_KEY=change-me
TOKEN_TTL_SECONDS=3600
```

## Adapter Settings

External systems usually deserve settings owned by the adapter or client that
uses them:

```python
from dataclasses import dataclass

from diwire import Injected
from pydantic_settings import BaseSettings, SettingsConfigDict


class SmtpEmailSenderSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SMTP_")

    host: str
    port: int = 587
    username: str
    password: str


@dataclass(kw_only=True, slots=True)
class SmtpEmailSender:
    _settings: Injected[SmtpEmailSenderSettings]

    def send_welcome_email(self, *, email: str) -> None:
        # Use self._settings to configure the SMTP client at the edge.
        raise NotImplementedError
```

Keep secrets out of code and tests. Use environment variables, `.env` files only
when the repo already supports them, or test-specific settings instances.

## Container Registration

Register settings instances in `ioc/` by default so environment loading happens
at the composition edge:

```python
from diwire import Container


def register_dependencies(container: Container) -> None:
    container.add_instance(TokenIssuerSettings(), provides=TokenIssuerSettings)
    container.add_instance(
        SmtpEmailSenderSettings(),
        provides=SmtpEmailSenderSettings,
    )
```

Do not construct settings inside the class that consumes them. Only allow
container auto-creation for settings when the repo has an explicit convention for
it and the environment-read side effect is still easy to locate and override.

## Test Overrides

Tests should pass or register explicit settings objects:

```python
def test_token_ttl() -> None:
    issuer = TokenIssuer(
        _settings=TokenIssuerSettings(
            secret_key="test-secret",
            ttl_seconds=60,
        ),
    )

    token = issuer.issue_token(user_id=123)

    assert token == "123:60"
```

For container tests, override the settings instance before resolving the object
graph.

## Guidance

- Use one settings class per consumer or tightly related adapter family.
- Use clear `env_prefix` values such as `TOKEN_`, `SMTP_`, `DATABASE_`, or
  `OPENAI_`.
- Keep settings classes focused on configuration only. Do not put business logic
  or client construction in settings classes.
- Do not import framework settings globals in core services.
- Do not call `os.getenv()` in application classes.
- Prefer required fields for secrets and connection details that must be present
  in real environments.
- Use defaults only for harmless operational values, not secrets.
