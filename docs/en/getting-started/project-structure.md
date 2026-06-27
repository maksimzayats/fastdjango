# Project Structure

Understanding the codebase organization is essential for working effectively with this template.

## Directory Overview

```
.
├── PROMPT_TEMPLATE.md      # Agent-led setup prompt for project creators
├── src/                    # Application source code
│   └── modern_python_template/         # Application package
│       ├── core/           # Business logic and domain models
│       ├── entrypoints/    # FastAPI, Django, and Celery composition roots
│       ├── foundation/     # Shared base contracts
│       ├── infrastructure/ # Cross-cutting concerns
│       └── ioc/            # Dependency injection container
├── management/             # Repository management commands
│   ├── dependency_updater.py # Dependency update helper
│   └── manage.py           # Django management entry point
├── tests/                  # Test suite
│   ├── integration/        # Integration tests
│   └── unit/               # Unit tests
├── docs/                   # Documentation (MkDocs)
├── docker/                 # Dockerfile and Compose service definitions
└── Makefile                # Common development commands
```

## Source Code Structure

### `src/modern_python_template/core/` - Business Logic

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
├── shared/                 # Shared component helpers
│   └── delivery/
│       └── fastapi/        # Request info and throttling helpers
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

### `src/modern_python_template/foundation/` - Base Contracts

Foundational marker and base classes live outside `core/`, `infrastructure/`,
and `entrypoints/` so every layer can depend on them without reversing
ownership:

```
foundation/
├── configurators.py        # BaseConfigurator
├── delivery/
│   ├── controllers.py      # BaseAsyncController
│   ├── celery/
│   │   └── schemas.py      # BaseCelerySchema
│   └── fastapi/
│       └── schemas.py      # BaseFastAPISchema
├── dtos.py                 # BaseDTO
├── factories.py            # BaseFactory
├── services.py             # BaseService
└── use_cases.py            # BaseUseCase
```

Celery's async task-controller bridge lives in `infrastructure/celery/` because
it adapts async application handlers to Celery's sync worker API.

### `src/modern_python_template/entrypoints/` - Composition Roots

Application bootstrapping, framework factories, route registration, task
registration, and Django URL configuration live outside `core/`:

```
entrypoints/
├── django/
│   ├── factories.py        # AdminSiteFactory, DjangoWSGIFactory
│   └── urls.py             # Django URLConf
├── fastapi/
│   ├── app.py              # ASGI app object
│   ├── bootstrap.py        # Container bootstrap
│   └── factories.py        # FastAPI app factory and route registration
└── celery/
    ├── app.py              # Celery app object
    ├── factories.py        # Celery app and task registration factories
    └── registry.py         # App task registry
```

### Domain Delivery

Delivery code lives inside the core package it exposes. For example, user FastAPI
controllers live in `core/user/delivery/fastapi/`, and the health ping task lives
in `core/health/delivery/celery/`.

Shared delivery helpers stay in `core/shared/delivery/`; reusable base contracts
stay in `foundation/`; application entry points and registries live in
`entrypoints/`. This keeps reusable code from importing concrete application
components.

### `src/modern_python_template/infrastructure/` - Cross-Cutting Concerns

Infrastructure code that supports all layers.

```
infrastructure/
├── anyio/                  # Thread pool configuration
├── celery/                 # Celery registry primitives
├── django/                 # Django setup, settings, middleware, transactions
├── logfire/                # OpenTelemetry/Logfire
├── logging/                # Logging configuration
├── throttled/              # Rate limiting
└── shared.py               # Base application settings
```

Key files:

- **`django/settings.py`**: Adapts Pydantic settings to Django's settings format
- **`django/transactions.py`**: Provides the injectable Django transaction factory
- **`logging/configurator.py`**: Configures application logging

### `src/modern_python_template/ioc/` - Dependency Injection

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
├── architecture/           # Project convention and structure checks
│   └── test_test_structure.py
├── foundation/             # Shared test base classes
│   └── factories.py        # BaseTestFactory, ContainerBasedFactory
├── integration/            # Integration tests
│   ├── conftest.py         # Integration fixtures (container, factories)
│   ├── factories.py        # Test factories
│   └── core/               # Mirrors src/modern_python_template/core
│       ├── authentication/
│       │   └── delivery/fastapi/test_controllers.py
│       ├── health/
│       │   └── delivery/
│       │       ├── celery/test_tasks.py
│       │       └── fastapi/test_controllers.py
│       └── user/
│           └── delivery/fastapi/test_controllers.py
└── unit/                   # Focused tests for reusable behavior
    ├── core/               # Mirrors src/modern_python_template/core
    └── infrastructure/     # Mirrors src/modern_python_template/infrastructure
```

Key components:

- **`integration/factories.py`**: `TestClientFactory`, `TestUserFactory`, `TestCeleryWorkerFactory`, `TestTasksRegistryFactory`
- **`integration/conftest.py`**: Function-scoped container fixtures for test isolation
- **`architecture/`**: Tests that enforce project structure and naming conventions

## Entry Points

The application has multiple entry points:

| Entry Point | File | Purpose |
|-------------|------|---------|
| FastAPI App | `src/modern_python_template/entrypoints/fastapi/app.py` | HTTP API application |
| Celery Worker | `src/modern_python_template/entrypoints/celery/app.py` | Background task processing |
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
| `docker/docker-compose.yaml` | Base Docker Compose services |
| `.env.example` | Environment variable template |
| `ruff.toml` | Ruff linter/formatter configuration |

## Next Steps

- [Development Environment](development-environment.md) - Set up your IDE
- [Service Layer Concept](../concepts/service-layer.md) - Understand the core pattern
- [Tutorial](../tutorial/index.md) - Learn by building a feature
