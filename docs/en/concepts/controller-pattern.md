# Controller Pattern

Controllers provide a unified async-first pattern for handling HTTP routes and
Celery tasks.

## The Core Abstraction

FastAPI controllers inherit from `BaseAsyncController`. Celery task controllers
inherit from `BaseCeleryTaskController`, which lets task handlers stay async
while Celery still receives a normal sync task callable.

```python
# Base controller shapes
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from celery import Celery, Task


@dataclass(kw_only=True)
class BaseAsyncController(ABC):
    @abstractmethod
    def register(self, registry: Any) -> None:
        """Register this controller with the appropriate registry."""
        ...

    async def handle_exception(self, exception: Exception) -> Any:
        """Handle exceptions raised by async controller methods."""
        raise exception


class BaseCeleryTaskController(BaseAsyncController):
    def _register_task(self, registry: Celery, *, name: str, handler: Callable) -> Task:
        """Register an async handler through the Celery sync boundary."""
        ...
```

## Key Features

### 1. The `register()` Method

Every controller implements `register()` to connect to its delivery mechanism:

```python
# HTTP Controller
def register(self, registry: APIRouter) -> None:
    registry.add_api_route("/v1/users", self.list_users, methods=["GET"])

# WebSocket Controller
def register(self, registry: APIRouter) -> None:
    registry.add_api_websocket_route("/v1/health/ws", self.health_check_websocket)

# Celery Task Controller
def register(self, registry: Celery) -> None:
    self._register_task(registry, name=PING_TASK_NAME, handler=self.ping)
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
            and not hasattr(BaseAsyncController, attr_name)
            and not attr_name.startswith("_")
            and attr_name not in dir(BaseAsyncController)
        ):
            setattr(self, attr_name, self._wrap_route(attr))

def _wrap_route(self, method: Callable[..., Any]) -> Callable[..., Any]:
    return self._add_exception_handler(method)
```

This means every public async endpoint automatically goes through
`handle_exception()` if it raises.
Use `BaseAsyncController` for FastAPI route methods and `BaseCeleryTaskController`
for Celery task handlers. The base classes fail fast when the handler style does
not match.

### 3. Custom Exception Handling

Override `handle_exception()` to map domain exceptions to responses:

```python
async def handle_exception(self, exception: Exception) -> Any:
    if isinstance(exception, TodoNotFoundError):
        raise HTTPException(status_code=404, detail=str(exception))
    if isinstance(exception, TodoAccessDeniedError):
        raise HTTPException(status_code=403, detail=str(exception))
    return await super().handle_exception(exception)
```

WebSocket handlers should accept the connection, delegate health or business
checks to use cases/services, send a small wire response, and close or continue
listening:

```python
async def health_check_websocket(self, websocket: WebSocket) -> None:
    await websocket.accept()
    await self._system_health_use_case.check()
    await websocket.send_json({"status": "ok"})
    await websocket.close()
```

## Transaction Boundaries

Controllers do not own database transactions. Keep transaction boundaries inside
small synchronous use-case or service methods, and inject `TransactionFactory`
there. FastAPI and Celery controllers stay async-first and delegate to the
application layer.

```python
@dataclass(kw_only=True)
class UserUseCase(BaseUseCase):
    _transaction_factory: Injected[TransactionFactory]

    async def create_user(self, *, data: CreateUserDTO) -> User:
        return await sync_to_async(
            self._create_user_transactionally,
            thread_sensitive=True,
        )(data=data)

    def _create_user_transactionally(self, *, data: CreateUserDTO) -> User:
        with self._transaction_factory(
            span_name="create user",
            use_case=type(self).__name__,
            method="_create_user_transactionally",
        ):
            return User.objects.create(...)
```

## HTTP Controller Example

```python
# src/modern_python_template/core/user/delivery/fastapi/controllers.py
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from modern_python_template.core.user.use_cases import UserUseCase
from modern_python_template.core.authentication.delivery.fastapi.auth import AuthenticatedRequest, JWTAuthFactory
from modern_python_template.foundation.delivery.controllers import BaseAsyncController


@dataclass(kw_only=True)
class UserController(BaseAsyncController):
    """HTTP controller for user operations."""

    _jwt_auth_factory: JWTAuthFactory
    _user_use_case: UserUseCase

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

    async def get_current_user(self, request: AuthenticatedRequest) -> UserSchema:
        return UserSchema.model_validate(request.state.user, from_attributes=True)

    async def handle_exception(self, exception: Exception) -> Any:
        if isinstance(exception, UserNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exception),
            ) from exception
        return await super().handle_exception(exception)
```

### Key Patterns

1. **Dataclass with `kw_only=True`**: Explicit named parameters
2. **Dependencies as fields**: `_user_use_case`, `_jwt_auth_factory`
3. **Computed values in `__post_init__`**: Create auth dependencies at initialization
4. **`__post_init__`**: Initialize auth dependencies, then call `super().__post_init__()`

## Celery Task Controller Example

```python
# src/modern_python_template/core/health/delivery/celery/tasks.py
from celery import Celery

from modern_python_template.core.health.delivery.celery.schemas import PingResultSchema
from modern_python_template.infrastructure.celery.controllers import BaseCeleryTaskController

PING_TASK_NAME = "ping"


@dataclass(kw_only=True)
class PingTaskController(BaseCeleryTaskController):
    """Simple task controller with no dependencies."""

    def register(self, registry: Celery) -> None:
        self._register_task(registry, name=PING_TASK_NAME, handler=self.ping)

    async def ping(self) -> PingResultSchema:
        return PingResultSchema(result="pong")
```

!!! note "Dataclass decorator"
    Concrete controllers use `@dataclass(kw_only=True)` even when they do not have dependencies. This keeps the injectable class shape consistent.

## Async HTTP Handlers

FastAPI controllers should expose async handlers:

```python
async def get_user(self, request: AuthenticatedRequest, user_id: int) -> UserSchema:
    user = await self._user_use_case.get_user_by_id(user_id=user_id)
    return UserSchema.model_validate(user, from_attributes=True)
```

If the workflow needs a Django transaction, the async use case calls a short sync
transactional method:

```python
from asgiref.sync import sync_to_async

async def create_user(self, *, data: CreateUserDTO) -> User:
    return await sync_to_async(
        self._create_user_transactionally,
        thread_sensitive=True,
    )(data=data)
```

## Controller Registration

Controllers are injected as fields into the factory and registered with tagged routers:

```python
# src/modern_python_template/entrypoints/fastapi/factories.py
@dataclass(kw_only=True)
class FastAPIFactory(BaseFactory):
    # Controllers are injected as fields (auto-resolved by IoC)
    _health_controller: HealthController
    _authentication_token_controller: AuthenticationTokenController
    _user_controller: UserController

    def _register_controllers(self, app: FastAPI) -> None:
        # Create routers with tags for OpenAPI grouping
        health_router = APIRouter(tags=["health"])
        self._health_controller.register(health_router)
        app.include_router(health_router)

        auth_router = APIRouter(tags=["auth", "token"])
        self._authentication_token_controller.register(auth_router)
        app.include_router(auth_router)

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

### 2. Transaction Tracing

`TransactionFactory` adds Logfire spans around explicit database transactions.

### 3. Exception Isolation

Exceptions are caught and handled uniformly.

### 4. Easy Testing

Test business logic at the use-case or service layer, and keep controller tests focused on delivery behavior:

```python
async def test_get_user_by_id(user_use_case: UserUseCase) -> None:
    user = await user_use_case.get_user_by_id(user_id=1)
    assert user is not None
```

## Summary

The controller pattern:

- **Unifies** request handling across HTTP and Celery
- **Enforces** consistent structure via `register()`
- **Wraps** methods with exception handling
- **Keeps** database transactions inside use cases and services
- **Enables** easy testing through dependency injection
