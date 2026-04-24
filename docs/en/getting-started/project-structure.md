# Project Structure

Understanding the codebase organization is essential for working effectively with this template.

## Directory Overview

```
.
├── src/                    # Application source code
│   └── fastdjango/         # Application package
│       ├── core/           # Business logic and domain models
│       ├── infrastructure/ # Cross-cutting concerns
│       ├── ioc/            # Dependency injection container
│       └── manage.py       # Django management entry point
├── tests/                  # Test suite
│   ├── integration/        # Integration tests
│   └── unit/               # Unit tests
├── docs/                   # Documentation (MkDocs)
├── docker/                 # Docker configuration
└── scripts/                # Utility scripts
```

## Source Code Structure

### `src/fastdjango/core/` - Business Logic

The core layer contains domain models, use cases, and each component's delivery code.
This is where application behavior lives.

```
core/
├── exceptions.py           # Base application exception
├── health/                 # Health check domain
│   ├── exceptions.py       # Health domain exceptions
│   ├── use_cases.py        # SystemHealthUseCase
│   └── delivery/           # Health FastAPI/Celery delivery
│       ├── fastapi/
│       │   ├── controllers.py
│       │   └── schemas.py
│       └── celery/
│           ├── tasks.py
│           └── schemas.py
├── authentication/         # Token/session authentication
│   ├── models.py           # RefreshSession
│   ├── dtos.py             # Token use-case DTOs
│   ├── exceptions.py       # Authentication exceptions
│   ├── use_cases.py        # TokenUseCase
│   ├── services/           # Token/session primitives
│   │   ├── jwt.py          # JWTService
│   │   └── refresh_session.py  # RefreshSessionService
│   └── delivery/
│       └── fastapi/
│           ├── auth.py         # JWT auth dependency
│           ├── controllers.py  # Token endpoints
│           ├── schemas.py      # Token schemas
│           └── throttling.py   # Authenticated-user throttling
├── shared/                 # Cross-domain application wiring
│   ├── dtos.py             # Base DTO configuration
│   └── delivery/
│       ├── django/         # Django URLs and WSGI factory
│       ├── fastapi/        # FastAPI app/bootstrap/factory/schemas/request/throttling
│       └── celery/         # Celery app/factory/registry/schemas
└── user/                   # User domain
    ├── models.py           # User
    ├── dtos.py             # User use-case DTOs
    ├── exceptions.py       # User domain exceptions
    ├── use_cases.py        # UserUseCase
    └── delivery/
        ├── django/
        │   └── admin.py
        └── fastapi/
            ├── controllers.py
            └── schemas.py
```

**Key principle**: Use cases encapsulate application behavior. Controllers never access models directly.
DTOs live beside use cases; delivery schemas have their own independent base and may inherit from DTOs only when the wire shape matches the use-case shape.

### Domain Delivery

Delivery code lives inside the core package it exposes. For example, user FastAPI
controllers live in `core/user/delivery/fastapi/`, and the health ping task lives
in `core/health/delivery/celery/`.

Shared application entry points and registries live in `core/shared/delivery/`.
This mirrors the `secondbrain` structure: `core/shared/delivery/django/urls.py`
is the Django URLConf, and `core/shared/delivery/fastapi/app.py` is the FastAPI
entry point.

### `src/fastdjango/infrastructure/` - Cross-Cutting Concerns

Infrastructure code that supports all layers.

```
infrastructure/
├── anyio/                  # Thread pool configuration
├── celery/                 # Celery registry primitives
├── delivery/               # Delivery infrastructure
│   └── controllers.py      # Base Controller classes
├── django/                 # Django setup and settings
├── logfire/                # OpenTelemetry/Logfire
├── logging/                # Logging configuration
├── throttled/              # Rate limiting
└── shared.py               # Base application settings
```

Key files:

- **`delivery/controllers.py`**: Defines `Controller` and `TransactionController` base classes
- **`django/settings.py`**: Adapts Pydantic settings to Django's settings format
- **`logging/configurator.py`**: Configures application logging

### `src/fastdjango/ioc/` - Dependency Injection

Container configuration.

```
ioc/
├── container.py            # get_container
└── registry.py             # Explicit dependency registrations
```

- **`container.py`**: Creates `diwire.Container` and configures Django, logging, Logfire, and instrumentation

## Tests Structure

```
tests/
├── conftest.py             # Shared fixtures
├── integration/            # Integration tests
│   ├── conftest.py         # Integration fixtures (container, factories)
│   ├── factories.py        # Test factories
│   ├── fastapi/            # FastAPI endpoint tests
│   │   └── test_v1_users.py
│   └── celery/             # Celery task tests
│       └── test_tasks.py
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
| FastAPI App | `src/fastdjango/core/shared/delivery/fastapi/app.py` | HTTP API application |
| Celery Worker | `src/fastdjango/core/shared/delivery/celery/app.py` | Background task processing |
| Django Admin | Mounted at `/django/admin/` | Administration interface |

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Delivery Layer                          │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  │
│  │        HTTP API         │  │      Celery Tasks       │  │
│  │   Domain Controllers    │  │   Domain Controllers    │  │
│  └───────────┬─────────────┘  └───────────┬─────────────┘  │
└──────────────┼────────────────────────────┼─────────────────┘
               │                            │
               ▼                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Core Layer                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            DTOs, Services and Use Cases              │   │
│  │   UserUseCase  │  TokenUseCase │  SystemHealthUseCase│   │
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
