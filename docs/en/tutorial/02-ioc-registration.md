# Step 2: IoC Registration

In this step, you will register the `TodoService` in the IoC (Inversion of Control) container so it can be automatically injected into controllers.

## Files Overview

| Action | File Path |
|--------|-----------|
| Modify | `src/ioc/registries/core.py` |

## Understanding the Container

The template uses [punq](https://github.com/bobthemighty/punq), a lightweight dependency injection container for Python. The container is configured in `src/ioc/container.py` and organized into registries by layer:

```
src/ioc/
├── container.py          # Main container factory
└── registries/
    ├── core.py           # Domain services and settings
    ├── delivery.py       # Controllers and factories
    └── infrastructure.py # Cross-cutting concerns (JWT, auth)
```

### Registration Flow

When the application starts, it creates a container and registers all dependencies:

```python
# src/ioc/container.py (simplified)
def get_container() -> Container:
    container = Container()
    register_core(container)           # Services, settings
    register_infrastructure(container) # JWT, auth
    register_delivery(container)       # Controllers
    return container
```

## Step 2.1: Register TodoService

Open `src/ioc/registries/core.py` and add the `TodoService` registration.

First, add the import at the top of the file:

```python title="src/ioc/registries/core.py" hl_lines="5"
from punq import Container, Scope

from configs.application import ApplicationSettings
from core.health.services import HealthService
from core.todo.services import TodoService  # Add this import
from core.user.services.user import UserService
```

Then add the registration in the `_register_services` function:

```python title="src/ioc/registries/core.py" hl_lines="4"
def _register_services(container: Container) -> None:
    container.register(HealthService, scope=Scope.singleton)
    container.register(UserService, scope=Scope.singleton)
    container.register(TodoService, scope=Scope.singleton)  # Add this line
```

### Complete Updated File

Here is the complete `src/ioc/registries/core.py` after the changes:

```python title="src/ioc/registries/core.py"
from punq import Container, Scope

from configs.application import ApplicationSettings
from core.health.services import HealthService
from core.todo.services import TodoService
from core.user.services.user import UserService


def register_core(container: Container) -> None:
    _register_settings(container)
    _register_services(container)


def _register_settings(container: Container) -> None:
    container.register(
        ApplicationSettings,
        factory=lambda: ApplicationSettings(),
        scope=Scope.singleton,
    )


def _register_services(container: Container) -> None:
    container.register(HealthService, scope=Scope.singleton)
    container.register(UserService, scope=Scope.singleton)
    container.register(TodoService, scope=Scope.singleton)
```

## Understanding Registration Options

The `container.register()` method supports several patterns:

### Type-Based Registration (Recommended)

```python
container.register(TodoService, scope=Scope.singleton)
```

The container automatically:

1. Inspects `TodoService.__init__` for dependencies
2. Resolves each dependency from the container
3. Creates an instance with the resolved dependencies

Since `TodoService` has no constructor dependencies, punq creates it with no arguments.

### Factory-Based Registration

For services that require special initialization:

```python
container.register(
    ApplicationSettings,
    factory=lambda: ApplicationSettings(),
    scope=Scope.singleton,
)
```

Use factories when:

- The service loads configuration from environment variables
- You need custom initialization logic
- The service requires arguments not managed by the container

### Instance/Factory Registration for Protocols

For mapping protocols to concrete implementations:

```python
container.register(
    ApplicationSettingsProtocol,
    factory=lambda: container.resolve(ApplicationSettings),
    scope=Scope.singleton,
)
```

Use this pattern when:

- You need to register a specific implementation for a protocol
- The instance is pre-created (e.g., a configuration object)

## Scopes

The container supports two scopes:

| Scope | Behavior |
|-------|----------|
| `Scope.singleton` | One instance shared across the application |
| `Scope.transient` | New instance created for each resolution |

!!! tip "When to Use Each Scope"
    - **Singleton**: Services that maintain state or are expensive to create
    - **Transient**: Services that should be fresh for each request

For most services in this template, `Scope.singleton` is appropriate because:

- Services are stateless (they don't store request-specific data)
- Creating new instances adds unnecessary overhead
- Django ORM handles database connections separately

## Step 2.2: Verify Registration

You can verify the registration works by testing in the Django shell:

```bash
python src/manage.py shell
```

```python
>>> from ioc.container import get_container
>>> from core.todo.services import TodoService
>>>
>>> container = get_container()
>>> service = container.resolve(TodoService)
>>> print(service)
<core.todo.services.TodoService object at 0x...>
>>>
>>> # Verify singleton behavior
>>> service2 = container.resolve(TodoService)
>>> print(service is service2)
True
```

!!! success "Registration Complete"
    If you see `True`, the service is properly registered as a singleton.

## How Dependency Resolution Works

When a controller depends on `TodoService`, the container automatically provides it:

```python
class TodoController(Controller):
    def __init__(self, todo_service: TodoService) -> None:
        self._todo_service = todo_service
```

The resolution chain works like this:

1. Container sees `TodoController` needs `TodoService`
2. Container looks up `TodoService` in its registrations
3. Container creates (or retrieves singleton) `TodoService`
4. Container creates `TodoController` with the resolved service

This automatic wiring eliminates manual dependency management and makes testing easier.

## What's Next

You have registered `TodoService` in the IoC container:

- [x] Added import for `TodoService`
- [x] Registered as a singleton
- [x] Verified resolution works

In the next step, you will create the HTTP API controller that uses this service.

[Continue to Step 3: HTTP API & Admin](03-http-api.md){ .md-button .md-button--primary }

---

!!! abstract "See Also"
    - [IoC Container](../concepts/ioc-container.md) - Deep dive into dependency injection with punq
