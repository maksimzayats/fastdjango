# Project Structure

Understanding the codebase organization is essential for working effectively with this template.

## Directory Overview

```
.
├── src/                    # Application source code
│   ├── configs/            # Configuration and settings
│   ├── core/               # Business logic and domain models
│   ├── delivery/           # External interfaces (HTTP, Celery)
│   ├── infrastructure/     # Cross-cutting concerns
│   └── ioc/                # Dependency injection container
├── tests/                  # Test suite
│   ├── integration/        # Integration tests
│   └── unit/               # Unit tests
├── docs/                   # Documentation (MkDocs)
├── docker/                 # Docker configuration
└── scripts/                # Utility scripts
```

## Source Code Structure

### `src/configs/` - Configuration

Application configuration using Pydantic Settings.

```
configs/
├── application.py          # Base application settings (environment, version)
├── django.py               # Django settings adapters
└── logging.py              # Structured logging configuration
```

Key files:

- **`application.py`**: Defines `ApplicationSettings` with environment detection
- **`django.py`**: Adapts Pydantic settings to Django's settings format

### `src/core/` - Business Logic

The core layer contains domain models and services. This is where business logic lives.

```
core/
├── exceptions.py           # Base application exception
├── health/                 # Health check domain
│   └── services.py         # HealthService
└── user/                   # User domain
    ├── models.py           # User, RefreshSession models
    └── services/           # User-related services
        ├── user.py         # UserService (CRUD)
        ├── jwt.py          # JWTService (token operations)
        └── refresh_session.py  # RefreshSessionService
```

**Key principle**: Services encapsulate all database operations. Controllers never access models directly.

### `src/delivery/` - External Interfaces

The delivery layer handles external communication (HTTP requests, Celery tasks).

```
delivery/
├── http/                   # HTTP API (FastAPI)
│   ├── app.py              # WSGI/ASGI entry point
│   ├── factories.py        # FastAPIFactory
│   ├── settings.py         # HTTP settings (CORS, hosts)
│   ├── auth/               # Authentication
│   │   └── jwt.py          # JWTAuthFactory, JWTAuth
│   ├── controllers/        # HTTP controllers
│   │   ├── health/         # Health endpoint
│   │   └── user/           # User endpoints
│   ├── django/             # Django integration
│   │   └── factories.py    # Admin, WSGI factories
│   └── services/           # Delivery-specific services
│       ├── request.py      # RequestInfoService
│       └── throttler.py    # Rate limiting
└── tasks/                  # Celery tasks
    ├── app.py              # Celery entry point
    ├── factories.py        # CeleryAppFactory
    ├── registry.py         # Task registry
    └── tasks/              # Task controllers
        └── ping.py         # Example ping task
```

### `src/infrastructure/` - Cross-Cutting Concerns

Infrastructure code that supports all layers.

```
infrastructure/
├── adapters/               # External service adapters
│   ├── database/           # Database settings
│   ├── redis/              # Redis settings
│   └── s3/                 # S3/MinIO settings
├── delivery/               # Delivery infrastructure
│   └── controllers.py      # Base Controller classes
└── frameworks/             # Framework integrations
    ├── anyio/              # Thread pool configuration
    ├── django/             # Django setup
    ├── logfire/            # OpenTelemetry/Logfire
    ├── punq/               # IoC container
    └── throttled/          # Rate limiting
```

Key files:

- **`delivery/controllers.py`**: Defines `Controller` and `TransactionController` base classes
- **`frameworks/punq/auto_registering.py`**: The `AutoRegisteringContainer` implementation

### `src/ioc/` - Dependency Injection

Container configuration and registration.

```
ioc/
├── container.py            # ContainerFactory
└── registries.py           # Explicit registrations
```

- **`container.py`**: Creates `AutoRegisteringContainer` and configures frameworks
- **`registries.py`**: Registers special cases (string-based lookups, protocol mappings)

## Tests Structure

```
tests/
├── conftest.py             # Shared fixtures
├── integration/            # Integration tests
│   ├── conftest.py         # Integration fixtures (container, factories)
│   ├── factories.py        # Test factories
│   └── http/               # HTTP endpoint tests
│       └── v1/
│           └── test_v1_users.py
└── unit/                   # Unit tests
    └── services/           # Service unit tests
```

Key components:

- **`integration/factories.py`**: `TestClientFactory`, `TestUserFactory`, `TestCeleryWorkerFactory`
- **`integration/conftest.py`**: Function-scoped container fixtures for test isolation

## Entry Points

The application has multiple entry points:

| Entry Point | File | Purpose |
|-------------|------|---------|
| HTTP API | `delivery/http/app.py` | FastAPI application |
| Celery Worker | `delivery/tasks/app.py` | Background task processing |
| Django Admin | Mounted at `/django/admin/` | Administration interface |

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Delivery Layer                          │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │        HTTP API         │  │      Celery Tasks       │  │
│  │      Controllers        │  │      Controllers        │  │
│  └───────────┬─────────────┘  └───────────┬─────────────┘  │
└──────────────┼────────────────────────────┼─────────────────┘
               │                            │
               ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Services                          │   │
│  │   UserService  │  JWTService   │  HealthService     │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                     Models                           │   │
│  │      User      │ RefreshSession │                   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project dependencies and tool configuration |
| `Makefile` | Development commands |
| `docker-compose.yml` | Local development services |
| `.env.example` | Environment variable template |
| `ruff.toml` | Ruff linter/formatter configuration |
| `mypy.ini` | Type checking configuration |

## Next Steps

- [Development Environment](development-environment.md) - Set up your IDE
- [Service Layer Concept](../concepts/service-layer.md) - Understand the core pattern
- [Tutorial](../tutorial/index.md) - Learn by building a feature
