# Step 3: HTTP API & Admin

Expose the Todo service via REST API with JWT authentication.

## What You'll Build

- Pydantic request/response schemas
- HTTP controller with CRUD endpoints
- JWT authentication for protected routes
- Django admin registration

## Files to Create/Modify

| Action | File Path |
|--------|-----------|
| Create | `src/modern_python_template/core/todo/delivery/fastapi/__init__.py` |
| Create | `src/modern_python_template/core/todo/delivery/fastapi/schemas.py` |
| Create | `src/modern_python_template/core/todo/delivery/fastapi/controllers.py` |
| Create | `src/modern_python_template/core/todo/delivery/django/__init__.py` |
| Create | `src/modern_python_template/core/todo/delivery/django/admin.py` |
| Modify | `src/modern_python_template/entrypoints/fastapi/factories.py` |

## Concept Reference

> **See also:** [Controller Pattern concept](../concepts/controller-pattern.md) for details on the controller architecture.

## Step 1: Create the Directory Structure

```bash
mkdir -p src/modern_python_template/core/todo/delivery/fastapi
touch src/modern_python_template/core/todo/delivery/fastapi/__init__.py
mkdir -p src/modern_python_template/core/todo/delivery/django
touch src/modern_python_template/core/todo/delivery/django/__init__.py
```

## Step 2: Define Pydantic Schemas

Create request and response schemas in `src/modern_python_template/core/todo/delivery/fastapi/schemas.py`:

```python
# src/modern_python_template/core/todo/delivery/fastapi/schemas.py
from datetime import datetime

from pydantic import Field

from modern_python_template.foundation.delivery.fastapi.schemas import BaseFastAPISchema


class CreateTodoRequestSchema(BaseFastAPISchema):
    """Request schema for creating a todo."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)


class UpdateTodoRequestSchema(BaseFastAPISchema):
    """Request schema for updating a todo."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    completed: bool | None = None


class TodoSchema(BaseFastAPISchema):
    """Response schema for a todo item."""

    id: int
    title: str
    description: str
    completed: bool
    created_at: datetime
    updated_at: datetime
    user_id: int


class TodoListSchema(BaseFastAPISchema):
    """Response schema for a list of todos."""

    todos: list[TodoSchema]
    count: int
```

Key points:

- **Validation**: Field constraints ensure data integrity
- **Separation**: Request schemas differ from response schemas
- **Type safety**: All fields have explicit types

## Step 3: Create the Controller

Create `src/modern_python_template/core/todo/delivery/fastapi/controllers.py`:

```python
# src/modern_python_template/core/todo/delivery/fastapi/controllers.py
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from modern_python_template.core.todo.exceptions import (
    TodoAccessDeniedError,
    TodoNotFoundError,
)
from modern_python_template.core.todo.services import (
    TodoService,
)
from modern_python_template.core.authentication.delivery.fastapi.auth import (
    AuthenticatedRequest,
    JWTAuthFactory,
)
from modern_python_template.core.todo.delivery.fastapi.schemas import (
    CreateTodoRequestSchema,
    TodoListSchema,
    TodoSchema,
    UpdateTodoRequestSchema,
)
from modern_python_template.foundation.delivery.controllers import BaseAsyncController


@dataclass(kw_only=True)
class TodoController(BaseAsyncController):
    """HTTP controller for todo operations."""

    _todo_service: TodoService
    _jwt_auth_factory: JWTAuthFactory

    def __post_init__(self) -> None:
        # Create JWT auth dependency
        self._jwt_auth = self._jwt_auth_factory()
        # Call parent to wrap methods with exception handling
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        """Register routes with the API router."""
        registry.add_api_route(
            path="/v1/todos",
            endpoint=self.list_todos,
            methods=["GET"],
            response_model=TodoListSchema,
            dependencies=[Depends(self._jwt_auth)],
        )
        registry.add_api_route(
            path="/v1/todos",
            endpoint=self.create_todo,
            methods=["POST"],
            response_model=TodoSchema,
            status_code=status.HTTP_201_CREATED,
            dependencies=[Depends(self._jwt_auth)],
        )
        registry.add_api_route(
            path="/v1/todos/{todo_id}",
            endpoint=self.get_todo,
            methods=["GET"],
            response_model=TodoSchema,
            dependencies=[Depends(self._jwt_auth)],
        )
        registry.add_api_route(
            path="/v1/todos/{todo_id}",
            endpoint=self.update_todo,
            methods=["PATCH"],
            response_model=TodoSchema,
            dependencies=[Depends(self._jwt_auth)],
        )
        registry.add_api_route(
            path="/v1/todos/{todo_id}",
            endpoint=self.delete_todo,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
            dependencies=[Depends(self._jwt_auth)],
        )

    async def list_todos(
        self,
        request: AuthenticatedRequest,
        completed: bool | None = Query(default=None),
    ) -> TodoListSchema:
        """List all todos for the authenticated user."""
        user = request.state.user
        todos = await self._todo_service.list_todos_for_user(
            user=user,
            completed=completed,
        )

        return TodoListSchema(
            todos=[
                TodoSchema.model_validate(todo, from_attributes=True)
                for todo in todos
            ],
            count=len(todos),
        )

    async def create_todo(
        self,
        request: AuthenticatedRequest,
        body: CreateTodoRequestSchema,
    ) -> TodoSchema:
        """Create a new todo."""
        user = request.state.user
        todo = await self._todo_service.create_todo(
            user=user,
            title=body.title,
            description=body.description,
        )

        return TodoSchema.model_validate(todo, from_attributes=True)

    async def get_todo(
        self,
        request: AuthenticatedRequest,
        todo_id: int,
    ) -> TodoSchema:
        """Get a specific todo by ID."""
        user = request.state.user
        todo = await self._todo_service.get_todo_by_id(todo_id=todo_id, user=user)

        return TodoSchema.model_validate(todo, from_attributes=True)

    async def update_todo(
        self,
        request: AuthenticatedRequest,
        todo_id: int,
        body: UpdateTodoRequestSchema,
    ) -> TodoSchema:
        """Update a todo."""
        user = request.state.user

        todo = await self._todo_service.update_todo(
            todo_id=todo_id,
            user=user,
            title=body.title,
            description=body.description,
            completed=body.completed,
        )

        return TodoSchema.model_validate(todo, from_attributes=True)

    async def delete_todo(
        self,
        request: AuthenticatedRequest,
        todo_id: int,
    ) -> None:
        """Delete a todo."""
        user = request.state.user
        await self._todo_service.delete_todo(todo_id=todo_id, user=user)

    async def handle_exception(self, exception: Exception) -> Any:
        """Map domain exceptions to HTTP responses."""
        if isinstance(exception, TodoNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exception),
            ) from exception

        if isinstance(exception, TodoAccessDeniedError):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exception),
            ) from exception

        return await super().handle_exception(exception)
```

## Key Controller Patterns

### BaseAsyncController

Extending `BaseAsyncController` provides:

- **Exception handling**: Public methods are wrapped with `handle_exception`
- **Async guardrails**: Non-async route methods fail fast

Keep Django transactions inside short sync service or use-case methods named
`*_transactionally`, called with `sync_to_async(..., thread_sensitive=True)`.
### JWT Authentication

The `JWTAuthFactory` creates authentication dependencies:

```python
# Basic auth - any authenticated user
self._jwt_auth = self._jwt_auth_factory()

# Staff only
self._staff_auth = self._jwt_auth_factory(require_staff=True)

# Superuser only
self._superuser_auth = self._jwt_auth_factory(require_superuser=True)
```

### AuthenticatedRequest

The `AuthenticatedRequest` type provides access to:

- `request.state.user` - The authenticated `User` instance
- `request.state.jwt_payload` - The decoded JWT claims

### Exception Mapping

Override `handle_exception` to map domain exceptions to HTTP responses:

| Domain Exception | HTTP Status |
|------------------|-------------|
| `TodoNotFoundError` | 404 Not Found |
| `TodoAccessDeniedError` | 403 Forbidden |

## Step 4: Register the Controller

Modify `src/modern_python_template/entrypoints/fastapi/factories.py` to include the TodoController:

```python
# src/modern_python_template/entrypoints/fastapi/factories.py
# Add this import at the top
from modern_python_template.core.todo.delivery.fastapi.controllers import TodoController


@dataclass(kw_only=True)
class FastAPIFactory(BaseFactory):
    # ... existing controller fields ...
    _todo_controller: TodoController  # Add this field

    def _register_controllers(self, app: FastAPI) -> None:
        # ... existing controller registrations ...

        # Register TodoController
        todo_router = APIRouter(tags=["todo"])
        self._todo_controller.register(todo_router)
        app.include_router(todo_router)
```

The controller is declared as a dataclass field and auto-resolved by the IoC container when `FastAPIFactory` is instantiated.

## Step 5: Register with Django Admin

Create `src/modern_python_template/core/todo/delivery/django/admin.py`:

```python
# src/modern_python_template/core/todo/delivery/django/admin.py
from django.contrib import admin

from modern_python_template.core.todo.models import Todo


@admin.register(Todo)
class TodoAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "completed", "created_at", "updated_at"]
    list_filter = ["completed", "created_at"]
    search_fields = ["title", "description", "user__username"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = [
        (None, {"fields": ["title", "description", "completed", "user"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]
```

Import the admin module from `TodoConfig.ready()` so Django registers it:

```python
# src/modern_python_template/core/todo/apps.py
def ready(self) -> None:
    from modern_python_template.core.todo.delivery.django import admin as _todo_admin  # noqa: F401, PLC0415
```

## Verification

### Test the API

1. Start the development server:

```bash
make dev
```

2. Open the API docs at http://localhost:8000/docs

3. First, create a user and get a token:

```bash
# Create user
curl -X POST http://localhost:8000/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "SecurePass123!"}'

# Get token
curl -X POST http://localhost:8000/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "SecurePass123!"}'
```

4. Use the token to create a todo:

```bash
curl -X POST http://localhost:8000/v1/todos \
  -H "Authorization: Bearer <your-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn modern-python-template", "description": "Complete the tutorial"}'
```

5. List todos:

```bash
curl http://localhost:8000/v1/todos \
  -H "Authorization: Bearer <your-access-token>"
```

### Test Django Admin

1. Create a superuser:

```bash
uv run python management/manage.py createsuperuser
```

2. Visit http://localhost:8000/django/admin/

3. Log in and navigate to Todo admin

## Summary

You've created:

- Pydantic schemas for request/response validation
- HTTP controller with CRUD endpoints
- JWT authentication on all routes
- Domain exception to HTTP status mapping
- Django admin for management UI

## Next Step

In [Step 4: Celery Tasks](04-celery-tasks.md), you'll add background task processing to clean up completed todos.
