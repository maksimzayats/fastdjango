# Controller Pattern

Controllers provide a unified pattern for handling requests from any source: HTTP, Celery, CLI, etc.

## The Core Abstraction

All controllers inherit from the base `Controller` class:

```python
# src/infrastructure/delivery/controllers.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(kw_only=True)
class Controller(ABC):
    def __post_init__(self) -> None:
        self._wrap_methods()

    @abstractmethod
    def register(self, registry: Any) -> None:
        """Register this controller with the appropriate registry."""
        ...

    def handle_exception(self, exception: Exception) -> Any:
        """Handle exceptions raised by controller methods."""
        raise exception
```

## Key Features

### 1. The `register()` Method

Every controller implements `register()` to connect to its delivery mechanism:

```python
# HTTP Controller
def register(self, registry: APIRouter) -> None:
    registry.add_api_route("/v1/users", self.list_users, methods=["GET"])

# Celery Task Controller
def register(self, registry: Celery) -> None:
    registry.task(name=TaskName.PING)(self.ping)
```

### 2. Automatic Exception Handling

The `__post_init__` method wraps all public methods with exception handling:

```python
def __post_init__(self) -> None:
    self._wrap_methods()

def _wrap_methods(self) -> None:
    for attr_name in dir(self):
        attr = getattr(self, attr_name)

        if (
            callable(attr)
            and not hasattr(Controller, attr_name)
            and not attr_name.startswith("_")
            and attr_name not in dir(Controller)
        ):
            setattr(self, attr_name, self._wrap_route(attr))

def _wrap_route(self, method: Callable[..., Any]) -> Callable[..., Any]:
    return self._add_exception_handler(method)
```

This means every public method automatically goes through `handle_exception()` if it raises.

### 3. Custom Exception Handling

Override `handle_exception()` to map domain exceptions to responses:

```python
def handle_exception(self, exception: Exception) -> Any:
    if isinstance(exception, TodoNotFoundError):
        raise HTTPException(status_code=404, detail=str(exception))
    if isinstance(exception, TodoAccessDeniedError):
        raise HTTPException(status_code=403, detail=str(exception))
    return super().handle_exception(exception)
```

## TransactionController

For database operations, use `TransactionController`:

```python
# src/infrastructure/delivery/controllers.py
from infrastructure.frameworks.logfire.transaction import traced_atomic


@dataclass(kw_only=True)
class TransactionController(Controller, ABC):
    def _wrap_route(self, method: Callable[..., Any]) -> Callable[..., Any]:
        method = self._add_transaction(method)
        return super()._wrap_route(method)

    def _add_transaction(self, method: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(method)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with traced_atomic(
                "controller transaction",
                controller=type(self).__name__,
                method=method.__name__,
            ):
                return method(*args, **kwargs)

        return wrapper
```

This wraps methods with:

- `traced_atomic` - Combined database transaction and Logfire tracing
- Controller and method names as span attributes

## HTTP Controller Example

```python
# src/delivery/http/controllers/user/controllers.py
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from core.user.services.user import UserService
from delivery.http.auth.jwt import AuthenticatedRequest, JWTAuthFactory
from infrastructure.delivery.controllers import TransactionController


@dataclass(kw_only=True)
class UserController(TransactionController):
    """HTTP controller for user operations."""

    _jwt_auth_factory: JWTAuthFactory
    _user_service: UserService

    def __post_init__(self) -> None:
        self._jwt_auth = self._jwt_auth_factory()
        self._staff_jwt_auth = self._jwt_auth_factory(require_staff=True)
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        registry.add_api_route(
            path="/v1/users/me",
            endpoint=self.get_current_user,
            methods=["GET"],
            response_model=UserSchema,
            dependencies=[Depends(self._jwt_auth)],
        )

    def get_current_user(self, request: AuthenticatedRequest) -> UserSchema:
        return UserSchema.model_validate(request.state.user, from_attributes=True)

    def handle_exception(self, exception: Exception) -> Any:
        if isinstance(exception, UserNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exception),
            ) from exception
        return super().handle_exception(exception)
```

### Key Patterns

1. **Dataclass with `kw_only=True`**: Explicit named parameters
2. **Dependencies as fields**: `_user_service`, `_jwt_auth_factory`
3. **Computed values in `__post_init__`**: Create auth dependencies at initialization
4. **`__post_init__`**: Initialize auth dependencies, then call `super().__post_init__()`

## Celery Task Controller Example

```python
# src/delivery/tasks/tasks/ping.py
from typing import Literal, TypedDict

from celery import Celery

from delivery.tasks.registry import TaskName
from infrastructure.delivery.controllers import Controller


class PingResult(TypedDict):
    result: Literal["pong"]


class PingTaskController(Controller):
    """Simple task controller with no dependencies."""

    def register(self, registry: Celery) -> None:
        registry.task(name=TaskName.PING)(self.ping)

    def ping(self) -> PingResult:
        return PingResult(result="pong")
```

!!! note "Dataclass decorator"
    Controllers without dependencies don't need the `@dataclass` decorator. The base `Controller` class already uses `@dataclass(kw_only=True)`, so subclasses inherit that behavior. Only add `@dataclass(kw_only=True)` when you have dependency fields to inject.

## Sync vs Async Handlers

### Prefer Sync Handlers

FastAPI runs sync handlers in a thread pool automatically:

```python
# ✅ Recommended - sync handler
def get_user(self, request: AuthenticatedRequest, user_id: int) -> UserSchema:
    user = self._user_service.get_user_by_id(user_id)
    return UserSchema.model_validate(user, from_attributes=True)
```

### Async When Needed

For truly async operations (external APIs, etc.):

```python
from asgiref.sync import sync_to_async

async def get_user_async(self, request: AuthenticatedRequest, user_id: int) -> UserSchema:
    user = await sync_to_async(
        self._user_service.get_user_by_id,
        thread_sensitive=False,  # Read-only = parallel OK
    )(user_id)
    return UserSchema.model_validate(user, from_attributes=True)
```

Thread sensitivity:

| `thread_sensitive` | Use Case |
|-------------------|----------|
| `False` | Read-only operations (SELECT) |
| `True` | Write operations (INSERT/UPDATE/DELETE) |

## Controller Registration

Controllers are injected as fields into the factory and registered with tagged routers:

```python
# src/delivery/http/factories.py
@dataclass(kw_only=True)
class FastAPIFactory:
    # Controllers are injected as fields (auto-resolved by IoC)
    _health_controller: HealthController
    _user_token_controller: UserTokenController
    _user_controller: UserController

    def _register_controllers(self, app: FastAPI) -> None:
        # Create routers with tags for OpenAPI grouping
        health_router = APIRouter(tags=["health"])
        self._health_controller.register(health_router)
        app.include_router(health_router)

        user_token_router = APIRouter(tags=["user", "token"])
        self._user_token_controller.register(user_token_router)
        app.include_router(user_token_router)

        user_router = APIRouter(tags=["user"])
        self._user_controller.register(user_router)
        app.include_router(user_router)
```

!!! tip "Controller injection"
    Controllers are declared as dataclass fields and auto-resolved by the IoC container when `FastAPIFactory` is resolved. This ensures all controller dependencies are properly injected.

## Benefits

### 1. Consistent Pattern

Same structure for HTTP and Celery:

```python
# Both have:
# - Dependencies as fields
# - register() method
# - handle_exception() for errors
```

### 2. Automatic Tracing

`TransactionController` adds Logfire spans automatically.

### 3. Exception Isolation

Exceptions are caught and handled uniformly.

### 4. Easy Testing

Mock dependencies, test business logic:

```python
def test_get_user():
    mock_service = MagicMock()
    controller = UserController(_user_service=mock_service, ...)
    # Test controller methods directly
```

## Summary

The controller pattern:

- **Unifies** request handling across HTTP and Celery
- **Enforces** consistent structure via `register()`
- **Wraps** methods with exception handling
- **Provides** `TransactionController` for database operations
- **Enables** easy testing through dependency injection
