# Step 2: IoC Registration

Understand how the dependency injection container wires services automatically with `diwire`.

## What You'll Learn

- How `get_container` builds the container
- How recursive auto-wiring works
- When to use `add`, `add_factory`, and `add_instance`

## Concept Reference

> **See also:** [IoC Container concept](../concepts/ioc-container.md)

## Container Creation

The container is created in `src/fastdjango/ioc/container.py`:

```python
from diwire import Container, DependencyRegistrationPolicy, MissingPolicy


def get_container(
    *,
    configure_django: bool = True,
    configure_logging: bool = True,
    configure_logfire: bool = True,
    instrument_libraries: bool = True,
) -> Container:
    container = Container(
        missing_policy=MissingPolicy.REGISTER_RECURSIVE,
        dependency_registration_policy=DependencyRegistrationPolicy.REGISTER_RECURSIVE,
    )

    if configure_django:
        _configure_django(container)

    if configure_logging:
        _configure_logging(container)

    if configure_logfire:
        _configure_logfire(container)

    if instrument_libraries:
        _instrument_libraries(container)

    register_dependencies(container)
    return container
```

Configuration components (`DjangoConfigurator`, `LoggingConfigurator`, telemetry instrumentor) are also resolved from this same container.

## Auto-Wiring Behavior

When you call `container.resolve(TodoService)`, `diwire`:

1. Inspects constructor type hints
2. Recursively resolves dependencies
3. Caches instances in root app scope (`Lifetime.SCOPED`)
4. Returns the instance

```python
service = container.resolve(TodoService)
service_again = container.resolve(TodoService)
assert service is service_again
```

## `FastAPIFactory` Resolution by Type

The HTTP app now resolves by type with delayed import:

```python
from fastdjango.ioc.container import get_container

_container = get_container()

from fastdjango.entrypoints.fastapi.factories import FastAPIFactory

api_factory = _container.resolve(FastAPIFactory)
```

No string-key registration is used.

## Manual Registration APIs

Use explicit registration only for special cases:

```python
# Class registration
container.add(ConcreteService)

# Factory registration
container.add_factory(
    lambda: container.resolve(ConcreteService),
    provides=ServiceProtocol,
)

# Instance override (tests)
container.add_instance(mock_service, provides=ConcreteService)
```

## Testing Rule: Override Early

Override before first resolve of anything that would cache the original dependency:

```python
mock = MagicMock(spec=TodoService)
container.add_instance(mock, provides=TodoService)

controller = container.resolve(TodoController)
```

## Summary

- `get_container` uses `diwire.Container` with recursive registration policies
- Dependencies are resolved by type, including `FastAPIFactory`
- Test overrides use `add_instance(..., provides=...)` before first resolve
