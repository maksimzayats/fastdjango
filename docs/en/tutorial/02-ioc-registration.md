# Step 2: IoC Registration

Understand how the dependency injection container automatically wires your services.

## What You'll Learn

- How `AutoRegisteringContainer` works
- When explicit registration is needed
- How to resolve dependencies

## Concept Reference

> **See also:** [IoC Container concept](../concepts/ioc-container.md) for detailed explanation.

## Understanding Auto-Registration

The project uses an `AutoRegisteringContainer` that automatically registers services when they're first resolved. This means:

**You don't need to register `TodoService` anywhere.**

When code requests `TodoService` from the container, it's automatically registered as a singleton.

## How It Works

### Step 1: Container Creation

The container is created in `src/ioc/container.py`:

```python
# src/ioc/container.py
class ContainerFactory:
    def __call__(
        self,
        *,
        configure_django: bool = True,
        configure_logging: bool = True,
        instrument_libraries: bool = True,
    ) -> AutoRegisteringContainer:
        container = AutoRegisteringContainer()

        if configure_django:
            self._configure_django(container)

        if configure_logging:
            self._configure_logging(container)

        if instrument_libraries:
            self._instrument_libraries(container)

        self._register(container)

        return container

    def _configure_django(self, container: AutoRegisteringContainer) -> None:
        configurator = container.resolve(DjangoConfigurator)
        configurator.configure(django_settings_module="configs.django")

    def _register(self, container: AutoRegisteringContainer) -> None:
        from ioc.registries import Registry

        registry = container.resolve(Registry)
        registry.register(container)
```

!!! note
    Configuration classes like `DjangoConfigurator` are resolved from the container, ensuring their dependencies are properly injected.

### Step 2: Auto-Registration Logic

When you resolve a service that isn't registered, the container:

1. Inspects the class's `__init__` method for type hints
2. Recursively resolves any dependencies
3. Registers the service as a singleton
4. Returns the instance

```python
# What happens internally when you resolve TodoService
container.resolve(TodoService)

# The container sees TodoService has no dependencies (empty __init__)
# It registers TodoService as a singleton
# It creates an instance and returns it
```

### Step 3: Dependency Resolution

If a service has dependencies, they're resolved recursively:

```python
# Example: A controller with dependencies
@dataclass(kw_only=True)
class TodoController(Controller):
    _todo_service: TodoService  # This gets auto-resolved

# When resolving TodoController:
# 1. Container sees _todo_service: TodoService
# 2. Container resolves TodoService (auto-registered if needed)
# 3. Container creates TodoController with TodoService instance
```

## What Gets Auto-Registered

| Type | Registration | Scope |
|------|--------------|-------|
| Regular classes | Automatically when first resolved | Singleton |
| Pydantic `BaseSettings` | Automatically with factory | Singleton |
| Protocols/Interfaces | Must be explicit | Explicit |
| String-based keys | Must be explicit | Explicit |

## Pydantic Settings Auto-Detection

Settings classes that inherit from `BaseSettings` are detected automatically:

```python
# src/core/user/services/jwt.py
class JWTServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JWT_")

    secret_key: str
    algorithm: str = "HS256"
```

When resolved, the container:

1. Detects it's a `BaseSettings` subclass
2. Registers with a factory: `lambda: JWTServiceSettings()`
3. The settings load from environment variables automatically

```python
# This just works - settings loaded from env
jwt_settings = container.resolve(JWTServiceSettings)
print(jwt_settings.secret_key)  # From JWT_SECRET_KEY env var
```

## Explicit Registration

Some cases require explicit registration in `src/ioc/registries.py`:

### String-Based Keys

When resolving by string instead of type:

```python
# src/ioc/registries.py
from punq import Container, Scope

from delivery.http.factories import FastAPIFactory


class Registry:
    def register(self, container: Container) -> None:
        # Using string-based registration to avoid loading django-related code too early
        container.register(
            "FastAPIFactory",
            factory=lambda: container.resolve(FastAPIFactory),
            scope=Scope.singleton,
        )
```

Usage:

```python
# Resolve by string
factory = container.resolve("FastAPIFactory")
```

### Protocol Mappings (Example)

When an interface should map to a concrete implementation:

```python
# Example pattern - not currently used in this codebase
class Registry:
    def register(self, container: Container) -> None:
        container.register(
            MyProtocol,
            factory=lambda: container.resolve(ConcreteImplementation),
            scope=Scope.singleton,
        )
```

## Verifying Registration

You can verify the container works correctly:

```python
# In a Python shell
from ioc.container import ContainerFactory
from core.todo.services import TodoService

# Create container
container = ContainerFactory()()

# Resolve service - auto-registered
service = container.resolve(TodoService)

# Resolve again - same instance (singleton)
service2 = container.resolve(TodoService)
assert service is service2  # Same object
```

## The Registration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    container.resolve(T)                     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Is T registered?  │
                    └─────────┬─────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼ Yes                           ▼ No
    ┌─────────────────┐            ┌─────────────────────────┐
    │ Return existing │            │ Check T's __init__ for  │
    │    instance     │            │    type annotations     │
    └─────────────────┘            └───────────┬─────────────┘
                                               │
                                               ▼
                                   ┌─────────────────────────┐
                                   │ Recursively resolve     │
                                   │     dependencies        │
                                   └───────────┬─────────────┘
                                               │
                                               ▼
                                   ┌─────────────────────────┐
                                   │ Register T as singleton │
                                   │   and return instance   │
                                   └─────────────────────────┘
```

## Best Practices

### Do: Use Type Hints

The container relies on type hints for dependency resolution:

```python
@dataclass(kw_only=True)
class MyService:
    _user_service: UserService  # Resolved automatically
    _jwt_settings: JWTServiceSettings  # Settings loaded from env
```

### Don't: Use `Any` Types

```python
# Bad - container can't resolve this
def __init__(self, service: Any) -> None:
    self._service = service
```

### Do: Keep `__init__` Simple

```python
# Good - dependencies are injected
@dataclass(kw_only=True)
class MyController(Controller):
    _todo_service: TodoService
```

### Don't: Create Dependencies in `__init__`

```python
# Bad - defeats the purpose of DI
def __init__(self) -> None:
    self._todo_service = TodoService()
```

## Summary

You've learned:

- The container auto-registers services when resolved
- Pydantic Settings load from environment variables automatically
- Only protocols and string-based keys need explicit registration
- Dependencies are resolved recursively via type hints

## Next Step

In [Step 3: HTTP API](03-http-api.md), you'll create REST endpoints for the todo service.
