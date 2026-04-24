# IoC Container

The Inversion of Control (IoC) container manages dependency injection and automatically wires object graphs from type hints.

## What is Dependency Injection?

Without DI, classes create dependencies directly:

```python
class UserController:
    def __init__(self) -> None:
        self._user_use_case = UserUseCase()
        self._jwt_service = JWTService()
```

With DI, dependencies are provided externally:

```python
class UserController:
    def __init__(self, user_use_case: UserUseCase, jwt_service: JWTService) -> None:
        self._user_use_case = user_use_case
        self._jwt_service = jwt_service
```

## The `diwire` Container

This project uses [`diwire`](https://pypi.org/project/diwire/). The container is configured to recursively auto-register missing dependencies.

```python
from diwire import Container

container = Container()
service = container.resolve(UserUseCase)
```

`resolve(UserUseCase)` recursively builds and caches dependencies in the app root scope.

## Container Creation

`src/fastdjango/ioc/container.py` creates and configures the container:

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

## Bootstrap Module for `FastAPIFactory`

The HTTP wiring creates the container in a bootstrap module, where `get_container` is invoked at import time:

```python
# src/fastdjango/core/shared/delivery/fastapi/bootstrap.py
from fastdjango.ioc.container import get_container

container = get_container()
```

Then the app entrypoint uses ordinary top-level imports (no delayed/lazy import behavior):

```python
from fastdjango.core.shared.delivery.fastapi.bootstrap import container
from fastdjango.core.shared.delivery.fastapi.factories import FastAPIFactory

api_factory = container.resolve(FastAPIFactory)
```

This keeps startup explicit and centralized in `bootstrap.py`.

## Registration APIs

Most services need no manual registration, but when needed use native `diwire` APIs:

```python
# Register a concrete class for itself
container.add(UserUseCase)

# Register a factory for an abstraction
container.add_factory(lambda: container.resolve(UserUseCase), provides=UserUseCaseProtocol)

# Register an existing instance/mock
container.add_instance(mock_service, provides=UserUseCase)
```

## Lifetime and Scope

`Scope` and `Lifetime` are `diwire` concepts, but this project does not pass
`root_scope` or `default_lifetime` to `Container()`.

The container setup in this codebase uses these `Container()` constructor options:

- `missing_policy=MissingPolicy.REGISTER_RECURSIVE`
- `dependency_registration_policy=DependencyRegistrationPolicy.REGISTER_RECURSIVE`

```python
from diwire import Container, DependencyRegistrationPolicy, MissingPolicy

container = Container(
    missing_policy=MissingPolicy.REGISTER_RECURSIVE,
    dependency_registration_policy=DependencyRegistrationPolicy.REGISTER_RECURSIVE,
)
```

`Scope`/`Lifetime` behavior therefore comes from `diwire` defaults unless you
explicitly override it when creating `Container()`.

## Pydantic Settings Integration

`diwire` resolves `BaseSettings` subclasses directly, so settings classes can be injected without custom wrappers.

```python
jwt_settings = container.resolve(JWTServiceSettings)
```

## Testing Overrides

Each test should get a fresh container. Override dependencies before first resolve of the target dependency graph.

```python
@pytest.fixture(scope="function")
def container() -> Container:
    return get_container()


def test_with_mock(container: Container) -> None:
    mock_service = MagicMock()
    container.add_instance(mock_service, provides=UserUseCase)

    controller = container.resolve(UserController)
    assert controller is not None
```
