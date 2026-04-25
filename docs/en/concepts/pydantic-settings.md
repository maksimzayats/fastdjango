# Pydantic Settings

Pydantic Settings provides type-safe configuration management by loading environment variables into validated Python objects.

## The Basic Pattern

Settings classes inherit from `BaseSettings`:

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class JWTServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JWT_")

    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
```

Environment variables:

```bash
JWT_SECRET_KEY=my-secret-key-with-at-least-32-bytes
JWT_ALGORITHM=HS512
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Result:

```python
settings = JWTServiceSettings()
settings.secret_key.get_secret_value()  # "my-secret-key"
settings.algorithm  # "HS512"
settings.access_token_expire_minutes  # 60
```

## Prefix Conventions

Settings classes use `env_prefix` to namespace variables:

| Prefix | Settings Class | Example Variables |
|--------|---------------|-------------------|
| `DJANGO_` | `DjangoSecuritySettings` | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` |
| `JWT_` | `JWTServiceSettings` | `JWT_SECRET_KEY`, `JWT_ALGORITHM` |
| `AWS_S3_` | `DjangoStorageSettings` | `AWS_S3_ACCESS_KEY_ID`, `AWS_S3_ENDPOINT_URL` |
| `CORS_` | `CORSSettings` | `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_METHODS` |
| `LOGFIRE_` | `LogfireSettings` | `LOGFIRE_ENABLED`, `LOGFIRE_TOKEN` |
| `INSTRUMENTOR_` | `InstrumentorSettings` | `INSTRUMENTOR_FASTAPI_EXCLUDED_URLS` |
| `ANYIO_` | `AnyIOSettings` | `ANYIO_THREAD_LIMITER_TOKENS` |
| `LOGGING_` | `LoggingSettings` | `LOGGING_LEVEL` |

Unprefixed variables:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `ENVIRONMENT` | Deployment environment |
| `ALLOWED_HOSTS` | Django allowed hosts |

## IoC Integration

`diwire` integrates with `pydantic-settings`, so `BaseSettings` subclasses can be resolved directly:

```python
# When resolving a settings class:
settings = container.resolve(JWTServiceSettings)

# The container resolves JWTServiceSettings directly.
# Values are loaded from environment sources during settings creation.
```

No explicit registration is needed for settings classes.

## Validation

Pydantic validates settings at startup:

```python
class DjangoDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: SecretStr  # Required - no default
    conn_max_age: int = 600
```

If `DATABASE_URL` is missing, the application fails fast with a clear error:

```
ValidationError: 1 validation error for DjangoDatabaseSettings
url
  field required
```

## Secret Handling

Use `SecretStr` for sensitive values:

```python
from pydantic import SecretStr


class JWTServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JWT_")

    secret_key: SecretStr  # Won't be logged accidentally


# Access the value explicitly
settings.secret_key.get_secret_value()
```

`SecretStr` prevents accidental logging:

```python
print(settings)  # secret_key='**********'
```

## Environment Files

The project loads `.env` files via `python-dotenv`:

```python
# src/fastdjango/infrastructure/django/configurator.py
from dotenv import load_dotenv

from fastdjango.foundation.configurators import BaseConfigurator


class DjangoConfigurator(BaseConfigurator):
    def configure(self) -> None:
        load_dotenv()  # Loads .env file
        # ...
```

For tests, `.env.test` is loaded when present; otherwise the committed
`.env.test.example` fallback is used:

```python
# tests/conftest.py
from dotenv import find_dotenv, load_dotenv

test_env_path = find_dotenv(".env.test", raise_error_if_not_found=False)
if test_env_path:
    load_dotenv(test_env_path, override=True)
else:
    load_dotenv(".env.test.example", override=True)
```

## Settings in Services

Inject settings into services:

```python
from fastdjango.foundation.services import BaseService

@dataclass(kw_only=True)
class JWTService(BaseService):
    _settings: JWTServiceSettings

    def issue_access_token(self, user_id: int) -> str:
        payload = {
            "sub": str(user_id),
            "exp": datetime.now(UTC)
            + timedelta(minutes=self._settings.access_token_expire_minutes),
        }
        return jwt.encode(
            payload,
            self._settings.secret_key.get_secret_value(),
            algorithm=self._settings.algorithm,
        )
```

The IoC container resolves settings automatically.

## Django Settings Adapter

Django settings are adapted from Pydantic using `PydanticSettingsAdapter`:

```python
# src/fastdjango/infrastructure/django/settings.py
class DjangoSecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DJANGO_")

    secret_key: str
    debug: bool = False


class DjangoDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: SecretStr
    conn_max_age: int = 600


# Adapter merges all settings into Django's settings dict
adapter = PydanticSettingsAdapter(
    DjangoSettings(),
    DjangoSecuritySettings(),
    DjangoDatabaseSettings(),
    # ...
)

# In Django settings file
adapter.adapt(locals())  # Populates locals() with settings
```

## Computed Fields

Use `@computed_field` for derived settings:

```python
from pydantic import computed_field


class DjangoStorageSettings(BaseSettings):
    model_config = SettingsConfigDict(populate_by_name=True)

    access_key_id: str = Field(validation_alias="AWS_S3_ACCESS_KEY_ID")
    secret_access_key: SecretStr = Field(validation_alias="AWS_S3_SECRET_ACCESS_KEY")
    endpoint_url: str = Field(validation_alias="AWS_S3_ENDPOINT_URL")
    public_endpoint_url: str | None = Field(
        default=None,
        validation_alias="AWS_S3_PUBLIC_ENDPOINT_URL",
    )
    public_bucket_name: str = Field(
        default="public",
        validation_alias="AWS_S3_PUBLIC_BUCKET_NAME",
    )
    protected_bucket_name: str = Field(
        default="protected",
        validation_alias="AWS_S3_PROTECTED_BUCKET_NAME",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def storages(self) -> dict[str, dict[str, str]]:
        """Generate Django STORAGES configuration."""
        base_options = {
            "access_key": self.access_key_id,
            "secret_key": self.secret_access_key.get_secret_value(),
            "endpoint_url": self.endpoint_url,
        }

        return {
            "default": {
                "BACKEND": "storages.backends.s3.S3Storage",
                "OPTIONS": {
                    **base_options,
                    "bucket_name": self.protected_bucket_name,
                },
            },
            "staticfiles": {
                "BACKEND": "storages.backends.s3.S3Storage",
                "OPTIONS": {
                    **base_options,
                    "bucket_name": self.public_bucket_name,
                },
            },
        }
```

## List and Complex Types

Parse complex values from environment:

```python
class FastAPISettings(BaseSettings):
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]


class CORSSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CORS_")

    allow_origins: list[str] = ["http://localhost"]
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]
    allow_credentials: bool = True
```

Environment:

```bash
ALLOWED_HOSTS=["localhost","127.0.0.1"]
CORS_ALLOW_ORIGINS=["https://example.com","https://app.example.com"]
```

## Best Practices

### Do: Group Related Settings

```python
# All JWT settings together
class JWTServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JWT_")
    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
```

### Do: Use Defaults for Optional Config

```python
class LogfireSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LOGFIRE_")

    enabled: bool = False  # Disabled by default
    token: SecretStr | None = None  # Optional
```

### Do: Validate at Startup

```python
# Settings validated when container creates them
container = get_container()
# If any required env vars are missing, fails here
```

### Don't: Access env Vars Directly

```python
# ❌ Not type-safe, no validation
secret = os.environ.get("JWT_SECRET_KEY")

# ✅ Type-safe, validated
secret = settings.secret_key.get_secret_value()
```

## Summary

Pydantic Settings:

- **Loads** environment variables into typed Python objects
- **Validates** configuration at startup
- **Uses** prefixes for namespacing
- **Integrates** with IoC container automatically
- **Protects** secrets with `SecretStr`
- **Supports** complex types and computed fields
