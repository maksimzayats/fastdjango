# IoC Container

The Inversion of Control (IoC) container manages dependency injection, automatically wiring components together.

## What is Dependency Injection?

Without DI, components create their own dependencies:

```python
# ❌ Without DI - hard to test, tightly coupled
class UserController:
    def __init__(self):
        self._user_service = UserService()  # Creates its own dependency
        self._jwt_service = JWTService()
```

With DI, dependencies are provided externally:

```python
# ✅ With DI - testable, loosely coupled
class UserController:
    def __init__(self, user_service: UserService, jwt_service: JWTService):
        self._user_service = user_service
        self._jwt_service = jwt_service
```

The IoC container is the "external provider" that creates and connects components.

## The punq Container

This project uses [punq](https://github.com/bobthemighty/punq), a lightweight Python DI container.

Basic usage:

```python
from punq import Container

container = Container()
container.register(UserService)  # Register service
service = container.resolve(UserService)  # Get instance
```

## AutoRegisteringContainer

The project extends punq with `AutoRegisteringContainer` that automatically registers services when resolved:

```python
# No explicit registration needed!
container = AutoRegisteringContainer()
service = container.resolve(UserService)  # Auto-registered and returned
```

### How It Works

When you resolve a type that isn't registered:

1. **Inspect `__init__`**: Check type annotations for dependencies
2. **Resolve dependencies**: Recursively resolve each dependency
3. **Register**: Add the type as a singleton
4. **Return instance**: Create and return the instance

```
container.resolve(UserController)
         │
         ▼
┌─────────────────────────────────────┐
│ UserController not registered       │
│ Check __init__ type annotations:    │
│   - user_service: UserService       │
│   - jwt_service: JWTService         │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Resolve UserService (recursively)   │
│ Resolve JWTService (recursively)    │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Register UserController as          │
│ singleton with resolved deps        │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Return UserController instance      │
└─────────────────────────────────────┘
```

### Pydantic Settings Detection

The container detects `BaseSettings` subclasses and registers them with a factory:

```python
class JWTServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="JWT_")
    secret_key: str
    algorithm: str = "HS256"

# Auto-registered with factory: lambda: JWTServiceSettings()
settings = container.resolve(JWTServiceSettings)
# settings.secret_key is loaded from JWT_SECRET_KEY env var
```

## Container Factory

The `ContainerFactory` creates configured containers:

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

        # It's required to configure Django before any registrations due to model imports
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

    def _configure_logging(self, container: AutoRegisteringContainer) -> None:
        configurator = container.resolve(LoggingConfigurator)
        configurator.configure()

    def _instrument_libraries(self, container: AutoRegisteringContainer) -> None:
        instrumentor = container.resolve(OpenTelemetryInstrumentor)
        instrumentor.instrument_libraries()

    def _register(self, container: AutoRegisteringContainer) -> None:
        # Import registry functions here to avoid imports before setting up Django
        from ioc.registries import Registry

        registry = container.resolve(Registry)
        registry.register(container)
```

Usage:

```python
container_factory = ContainerFactory()
container = container_factory()  # Fully configured container
```

!!! note "Auto-resolved configurators"
    Notice that configurators like `DjangoConfigurator` and `LoggingConfigurator` are resolved from the container. This ensures their dependencies (like settings classes) are properly injected.

## Explicit Registration

Most services don't need explicit registration. However, some cases require it:

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
factory = container.resolve("FastAPIFactory")
```

### Protocol Mappings (Example Pattern)

When an interface should resolve to a concrete implementation:

```python
# Example - not in current codebase
class Registry:
    def register(self, container: Container) -> None:
        container.register(
            SettingsProtocol,
            factory=lambda: container.resolve(ConcreteSettings),
            scope=Scope.singleton,
        )
```

!!! note
    The current codebase only uses string-based registration for `FastAPIFactory`. Protocol mappings shown above are an example pattern you might use when abstracting interfaces.

## Scopes

The container supports different scopes:

| Scope | Behavior |
|-------|----------|
| `singleton` | One instance per container (default) |
| `transient` | New instance each time |

Auto-registered services use singleton scope by default.

## Singleton Behavior

With singleton scope, resolving the same type returns the same instance:

```python
service1 = container.resolve(UserService)
service2 = container.resolve(UserService)
assert service1 is service2  # Same instance
```

This is important for stateful services and performance.

## Testing with IoC

### Per-Test Containers

Each test gets a fresh container:

```python
@pytest.fixture(scope="function")
def container() -> AutoRegisteringContainer:
    return ContainerFactory()()
```

### Overriding Registrations

Register mocks before resolving:

```python
def test_with_mock(container: AutoRegisteringContainer) -> None:
    mock_service = MagicMock()
    container.register(UserService, instance=mock_service)

    controller = container.resolve(UserController)
    # controller._user_service is the mock
```

### Test Factories

Use container-based factories for test setup:

```python
class TestClientFactory(ContainerBasedFactory):
    def __init__(self, container: AutoRegisteringContainer) -> None:
        self._container = container

    def __call__(self, auth_for_user: User | None = None) -> TestClient:
        # Uses container to resolve dependencies
        ...
```

## Best Practices

### Do: Use Type Hints

```python
@dataclass(kw_only=True)
class MyService:
    _other_service: OtherService  # Resolved automatically
```

### Don't: Use `Any` or Missing Hints

```python
# ❌ Container can't resolve this
def __init__(self, service: Any) -> None:
    ...
```

### Do: Keep Dependencies Explicit

```python
# ✅ Clear dependencies in __init__
@dataclass(kw_only=True)
class OrderService:
    _user_service: UserService
    _payment_service: PaymentService
```

### Don't: Create Dependencies Internally

```python
# ❌ Defeats the purpose of DI
def __init__(self) -> None:
    self._service = UserService()
```

### Do: Use Dataclasses

```python
@dataclass(kw_only=True)
class MyController(Controller):
    _service: MyService
```

The `kw_only=True` ensures explicit naming when constructing.

## Summary

The IoC container:

- **Auto-registers** services when resolved
- **Detects** Pydantic settings and loads from environment
- **Resolves** dependency graphs recursively
- **Uses** singleton scope by default
- **Enables** easy testing with overrides
