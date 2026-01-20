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
    access_token_expire_minutes: int = 30
```

Environment variables:

```bash
JWT_SECRET_KEY=my-secret-key
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
| `AWS_S3_` | `AWSS3Settings` | `AWS_S3_ACCESS_KEY_ID`, `AWS_S3_BUCKET_NAME` |
| `CORS_` | `CORSSettings` | `CORS_ALLOW_ORIGINS`, `CORS_ALLOW_METHODS` |
| `LOGFIRE_` | `LogfireSettings` | `LOGFIRE_ENABLED`, `LOGFIRE_TOKEN` |
| `ANYIO_` | `AnyIOSettings` | `ANYIO_THREAD_LIMITER_TOKENS` |
| `LOGGING_` | (logging config) | `LOGGING_LEVEL` |

Unprefixed variables:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `ENVIRONMENT` | Deployment environment |
| `ALLOWED_HOSTS` | Django allowed hosts |

## Auto-Registration in IoC

The `AutoRegisteringContainer` detects `BaseSettings` subclasses and registers them with a factory:

```python
# When resolving a settings class:
settings = container.resolve(JWTServiceSettings)

# The container automatically:
# 1. Detects it's a BaseSettings subclass
# 2. Registers with factory: lambda: JWTServiceSettings()
# 3. Settings load from environment on first access
```

No explicit registration is needed for settings classes.

## Validation

Pydantic validates settings at startup:

```python
class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATABASE_")

    url: str  # Required - no default
    pool_size: int = Field(default=5, ge=1, le=100)
    timeout: int = Field(default=30, ge=1)
```

If `DATABASE_URL` is missing, the application fails fast with a clear error:

```
ValidationError: 1 validation error for DatabaseSettings
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
# src/infrastructure/frameworks/django/configurator.py
from dotenv import load_dotenv


class DjangoConfigurator:
    def configure(self) -> None:
        load_dotenv()  # Loads .env file
        # ...
```

For tests, `.env.test` is loaded:

```python
# tests/conftest.py
from dotenv import load_dotenv

load_dotenv(".env.test")
```

## Settings in Services

Inject settings into services:

```python
@dataclass(kw_only=True)
class JWTService:
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
# src/configs/django.py
class DjangoSecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DJANGO_")

    secret_key: str
    debug: bool = False


class DjangoDatabaseSettings(BaseSettings):
    # Multiple settings combined
    url: str = Field(alias="DATABASE_URL")
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
    model_config = SettingsConfigDict(env_prefix="AWS_S3_")

    access_key_id: str
    secret_access_key: SecretStr
    bucket_name: str
    endpoint_url: str
    region_name: str = "us-east-1"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def storages(self) -> dict[str, dict[str, str]]:
        """Generate Django STORAGES configuration."""
        return {
            "default": {
                "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
                "OPTIONS": {
                    "access_key": self.access_key_id,
                    "secret_key": self.secret_access_key.get_secret_value(),
                    "bucket_name": self.bucket_name,
                    "endpoint_url": self.endpoint_url,
                },
            },
            "staticfiles": {
                "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
                "OPTIONS": {
                    "bucket_name": self.bucket_name,
                    "endpoint_url": self.endpoint_url,
                },
            },
        }
```

## List and Complex Types

Parse complex values from environment:

```python
class HTTPSettings(BaseSettings):
    allowed_hosts: list[str] = ["*"]  # From ALLOWED_HOSTS="host1,host2"
    csrf_trusted_origins: list[str] = []


class CORSSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CORS_")

    allow_origins: list[str] = ["*"]
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
    access_token_expire_minutes: int = 30
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
container = ContainerFactory()()
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
