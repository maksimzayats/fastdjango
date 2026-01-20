# Step 5: Observability

Configure logging, tracing, and monitoring for your application.

## What You'll Learn

- Structured logging with Logfire
- OpenTelemetry tracing
- Health check endpoints
- Custom span attributes

## Concept Reference

> **See also:** [Configure Observability guide](../how-to/configure-observability.md) for production setup.

## Understanding the Observability Stack

The project uses [Logfire](https://pydantic.dev/logfire) (built on OpenTelemetry) for observability:

- **Logging**: Structured logs with context
- **Tracing**: Distributed request tracing
- **Metrics**: Performance measurements
- **Instrumentation**: Auto-instrumented libraries

## Step 1: Enable Logfire Locally

Set environment variables in your `.env`:

```bash
# Enable Logfire
LOGFIRE_ENABLED=true

# Your Logfire token (get from https://logfire.pydantic.dev)
LOGFIRE_TOKEN=your-token-here
```

If you don't have a Logfire account, the application still works with console logging.

## Step 2: Understand Automatic Instrumentation

The project automatically instruments these libraries:

| Library | What's Traced |
|---------|---------------|
| Django | ORM queries, middleware |
| FastAPI | HTTP requests, routes |
| Celery | Task execution |
| Psycopg | Database queries |
| Redis | Cache operations |
| HTTPX | Outbound HTTP calls |
| Pydantic | Validation |

This is configured in `src/infrastructure/frameworks/logfire/instrumentor.py`.

## Step 3: Add Custom Logging

Use structured logging in your services:

```python
# src/core/todo/services.py
import logfire


@dataclass(kw_only=True)
class TodoService:
    def create_todo(
        self,
        user: User,
        *,
        title: str,
        description: str = "",
    ) -> Todo:
        # Log with structured context
        logfire.info(
            "Creating todo for user",
            user_id=user.id,
            title=title,
        )

        todo = Todo.objects.create(
            user=user,
            title=title,
            description=description,
        )

        logfire.info(
            "Todo created successfully",
            todo_id=todo.id,
            user_id=user.id,
        )

        return todo
```

### Log Levels

| Level | Use Case |
|-------|----------|
| `logfire.debug()` | Detailed debugging info |
| `logfire.info()` | Normal operations |
| `logfire.warn()` | Unexpected but handled situations |
| `logfire.error()` | Errors that need attention |

## Step 4: Add Custom Spans

Create spans for complex operations:

```python
# src/core/todo/services.py
import logfire


@dataclass(kw_only=True)
class TodoService:
    def delete_completed_todos(self, user: User) -> int:
        with logfire.span(
            "delete_completed_todos",
            user_id=user.id,
        ) as span:
            deleted_count, _ = Todo.objects.filter(
                user=user,
                completed=True,
            ).delete()

            # Add result as span attribute
            span.set_attribute("deleted_count", deleted_count)

            return deleted_count
```

## Step 5: TransactionController Tracing

The `TransactionController` uses `traced_atomic` to combine database transactions with Logfire tracing:

```python
# src/infrastructure/delivery/controllers.py
from infrastructure.frameworks.logfire.transaction import traced_atomic


@dataclass(kw_only=True)
class TransactionController(Controller, ABC):
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

When you extend `TransactionController`, every public method automatically gets:

- **Database transaction**: Wrapped in `@transaction.atomic`
- **Logfire span**: Named "controller transaction" with attributes
- **Span attributes**: Controller name and method name for filtering

```python
# Automatically traced when extending TransactionController
@dataclass(kw_only=True)
class TodoController(TransactionController):
    def list_todos(self, request: AuthenticatedRequest) -> TodoListSchema:
        # This method is automatically wrapped with traced_atomic:
        # - Span name: "controller transaction"
        # - Span attributes: controller="TodoController", method="list_todos"
        ...
```

## Step 6: Health Check Endpoint

The project includes a health check endpoint at `GET /v1/health`:

```python
# src/delivery/http/controllers/health/controllers.py
@dataclass(kw_only=True)
class HealthController(TransactionController):
    _health_service: HealthService

    def check_health(self) -> dict[str, str]:
        self._health_service.check_system_health()
        return {"status": "ok"}
```

The `HealthService` checks database connectivity:

```python
# src/core/health/services.py
class HealthService:
    def check_system_health(self) -> None:
        try:
            # Verify database connection
            Session.objects.first()
        except Exception as e:
            raise HealthCheckError("Database unavailable") from e
```

## Step 7: Configure Logging Level

Set the logging level via environment variable:

```bash
# Options: DEBUG, INFO, WARNING, ERROR
LOGGING_LEVEL=INFO
```

For local development, use `DEBUG`:

```bash
LOGGING_LEVEL=DEBUG
```

## Viewing Traces

### With Logfire Dashboard

1. Go to https://logfire.pydantic.dev
2. Select your project
3. View traces, logs, and metrics

### Without Logfire (Console)

When `LOGFIRE_ENABLED=false`, logs go to the console with structured output.

## Best Practices

### Do: Use Structured Logging

```python
# Good - structured context
logfire.info(
    "User action completed",
    user_id=user.id,
    action="create_todo",
    todo_id=todo.id,
)

# Bad - string interpolation
logfire.info(f"User {user.id} created todo {todo.id}")
```

### Do: Add Context to Spans

```python
with logfire.span("process_batch") as span:
    span.set_attribute("batch_size", len(items))
    span.set_attribute("batch_type", "todos")
```

### Don't: Log Sensitive Data

```python
# Bad - logs password
logfire.info("User login", password=password)

# Good - only log necessary data
logfire.info("User login attempt", username=username)
```

### Do: Use Appropriate Log Levels

```python
logfire.debug("Entering function", args=args)  # Verbose debugging
logfire.info("Processing request")             # Normal operation
logfire.warn("Retry attempt", attempt=2)       # Unexpected but handled
logfire.error("Failed to process", error=e)    # Needs attention
```

## Sensitive Data Scrubbing

Logfire is configured to scrub sensitive fields:

```python
# src/infrastructure/frameworks/logfire/configurator.py
logfire.configure(
    scrubbing=logfire.ScrubbingOptions(
        extra_patterns=["access_token", "refresh_token"],
    ),
)
```

This ensures tokens and secrets don't appear in logs.

## Summary

You've learned:

- How to enable Logfire observability
- Automatic instrumentation for common libraries
- Adding custom logs and spans
- Health check endpoint for monitoring
- Best practices for structured logging

## Next Step

In [Step 6: Testing](06-testing.md), you'll write comprehensive tests for your todo feature.
