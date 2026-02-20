# IoC Container

The Inversion of Control (IoC) container manages dependency injection and automatically wires object graphs from type hints.

## What is Dependency Injection?

Without DI, classes create dependencies directly:

```python
class UserController:
    def __init__(self) -> None:
        self._user_service = UserService()
        self._jwt_service = JWTService()
```

With DI, dependencies are provided externally:

```python
class UserController:
    def __init__(self, user_service: UserService, jwt_service: JWTService) -> None:
        self._user_service = user_service
        self._jwt_service = jwt_service
```

## The `diwire` Container

This project uses [`diwire`](https://pypi.org/project/diwire/). The container is configured to recursively auto-register missing dependencies.

```python
from diwire import Container

container = Container()
service = container.resolve(UserService)
```

`resolve(UserService)` recursively builds and caches dependencies in the app root scope.

## Container Factory

`src/ioc/container.py` creates and configures the container:

```python
from diwire import Container, DependencyRegistrationPolicy, MissingPolicy


class ContainerFactory:
    def __call__(
        self,
        *,
        configure_django: bool = True,
        configure_logging: bool = True,
        instrument_libraries: bool = True,
    ) -> Container:
        container = Container(
            missing_policy=MissingPolicy.REGISTER_RECURSIVE,
            dependency_registration_policy=DependencyRegistrationPolicy.REGISTER_RECURSIVE,
        )

        if configure_django:
            self._configure_django(container)

        if configure_logging:
            self._configure_logging(container)

        if instrument_libraries:
            self._instrument_libraries(container)

        return container
```

## Bootstrap Module for `FastAPIFactory`

The HTTP wiring creates the container in a bootstrap module, where `ContainerFactory` is invoked at import time:

```python
# src/delivery/http/bootstrap.py
from ioc.container import ContainerFactory

_container_factory = ContainerFactory()
container = _container_factory()
```

Then the app entrypoint uses ordinary top-level imports (no delayed/lazy import behavior):

```python
from delivery.http.bootstrap import container
from delivery.http.factories import FastAPIFactory

api_factory = container.resolve(FastAPIFactory)
```

This keeps startup explicit and centralized in `bootstrap.py`.

## Registration APIs

Most services need no manual registration, but when needed use native `diwire` APIs:

```python
# Register a concrete class for itself
container.add(UserService)

# Register a factory for an abstraction
container.add_factory(lambda: container.resolve(UserService), provides=UserServiceProtocol)

# Register an existing instance/mock
container.add_instance(mock_service, provides=UserService)
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
    return ContainerFactory()()


def test_with_mock(container: Container) -> None:
    mock_service = MagicMock()
    container.add_instance(mock_service, provides=UserService)

    controller = container.resolve(UserController)
    assert controller is not None
```
