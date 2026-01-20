# Configure Observability

Set up logging, tracing, and monitoring with Logfire.

## Goal

Enable comprehensive observability for your application.

## Prerequisites

- Application running locally
- (Optional) Logfire account for dashboard access

## What Gets Instrumented

The project auto-instruments:

| Library | What's Traced |
|---------|---------------|
| FastAPI | HTTP requests, routes, response times |
| Django | ORM queries, middleware |
| Celery | Task execution, queue times |
| Psycopg | Database queries |
| Redis | Cache operations |
| HTTPX | Outbound HTTP calls |
| Pydantic | Validation |

## Step-by-Step

### 1. Enable Logfire

Edit your `.env` file:

```bash
# Enable Logfire
LOGFIRE_ENABLED=true

# Your Logfire token (get from https://logfire.pydantic.dev)
LOGFIRE_TOKEN=your-token-here
```

!!! tip "Without Logfire Account"
    If you don't have a Logfire account, set `LOGFIRE_ENABLED=false`. Logs will go to the console with structured output.

### 2. Set Logging Level

```bash
# Options: DEBUG, INFO, WARNING, ERROR
LOGGING_LEVEL=INFO
```

For development:

```bash
LOGGING_LEVEL=DEBUG
```

### 3. Restart the Application

```bash
make dev
```

You should see Logfire initialization in the logs.

## Adding Custom Logging

### Basic Logging

```python
import logfire


def process_order(order_id: int) -> None:
    logfire.info("Processing order", order_id=order_id)

    # ... process ...

    logfire.info("Order processed", order_id=order_id, status="success")
```

### Log Levels

```python
logfire.debug("Detailed debug info", data=data)    # Verbose
logfire.info("Normal operation")                    # Standard
logfire.warn("Unexpected but handled", attempt=2)   # Caution
logfire.error("Operation failed", error=str(e))     # Needs attention
```

### Structured Context

Always use keyword arguments for structured data:

```python
# Good - structured, searchable
logfire.info(
    "User action",
    user_id=user.id,
    action="create_order",
    order_id=order.id,
    amount=order.total,
)

# Bad - string interpolation
logfire.info(f"User {user.id} created order {order.id}")
```

## Adding Custom Spans

### Basic Span

```python
import logfire


def complex_operation(items: list[Item]) -> Result:
    with logfire.span("complex_operation", item_count=len(items)):
        # ... process items ...
        return result
```

### Span with Attributes

```python
def batch_process(items: list[Item]) -> BatchResult:
    with logfire.span("batch_process") as span:
        span.set_attribute("input_count", len(items))

        processed = []
        for item in items:
            result = process_item(item)
            processed.append(result)

        span.set_attribute("processed_count", len(processed))
        span.set_attribute("success_rate", len(processed) / len(items))

        return BatchResult(items=processed)
```

### Nested Spans

```python
def process_order(order_id: int) -> Order:
    with logfire.span("process_order", order_id=order_id):
        order = self._order_service.get_order(order_id)

        with logfire.span("validate_payment"):
            self._payment_service.validate(order)

        with logfire.span("update_inventory"):
            self._inventory_service.reserve(order.items)

        with logfire.span("send_confirmation"):
            self._notification_service.send(order.user_id)

        return order
```

## TransactionController Tracing

`TransactionController` automatically creates spans:

```python
@dataclass(kw_only=True)
class OrderController(TransactionController):
    def create_order(self, body: CreateOrderSchema) -> OrderSchema:
        # Automatically wrapped with span:
        # "OrderController.create_order"
        # Plus transaction management
        ...
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

Fields containing these patterns are replaced with `[Scrubbed]`.

### Adding Custom Scrub Patterns

Edit `src/infrastructure/frameworks/logfire/configurator.py`:

```python
logfire.configure(
    scrubbing=logfire.ScrubbingOptions(
        extra_patterns=[
            "access_token",
            "refresh_token",
            "password",
            "secret",
            "api_key",
            "credit_card",
        ],
    ),
)
```

## Health Checks

The project includes a health endpoint at `GET /v1/health`:

```bash
curl http://localhost:8000/v1/health
```

Response:

```json
{"status": "ok"}
```

If database is unavailable:

```json
{"detail": "Database unavailable"}
```

With HTTP 503 status.

## Viewing Traces

### With Logfire Dashboard

1. Go to https://logfire.pydantic.dev
2. Select your project
3. View:
   - **Traces**: Request flow through services
   - **Logs**: Structured log entries
   - **Metrics**: Performance measurements

### Console Output

When `LOGFIRE_ENABLED=false`, structured logs go to console:

```
2024-01-15 10:30:45 INFO Processing order order_id=123
2024-01-15 10:30:46 INFO Payment validated order_id=123 amount=99.99
2024-01-15 10:30:46 INFO Order complete order_id=123 status=success
```

## Environment-Specific Configuration

### Development

```bash
LOGFIRE_ENABLED=false
LOGGING_LEVEL=DEBUG
```

### Staging

```bash
LOGFIRE_ENABLED=true
LOGFIRE_TOKEN=staging-token
LOGGING_LEVEL=INFO
```

### Production

```bash
LOGFIRE_ENABLED=true
LOGFIRE_TOKEN=production-token
LOGGING_LEVEL=WARNING
```

## Celery Observability

Celery tasks are automatically instrumented. For additional logging:

```python
import logfire


class SendEmailTaskController(Controller):
    def send_email(self, user_id: int, subject: str) -> SendResult:
        logfire.info("Starting email send", user_id=user_id)

        try:
            result = self._email_service.send(...)
            logfire.info("Email sent", user_id=user_id, message_id=result.id)
            return SendResult(success=True)
        except Exception as e:
            logfire.error("Email failed", user_id=user_id, error=str(e))
            return SendResult(success=False)
```

## Best Practices

1. **Use structured logging**: Keyword arguments, not string interpolation
2. **Add context**: Include IDs and relevant data in logs
3. **Choose appropriate levels**: DEBUG for verbose, INFO for normal, ERROR for problems
4. **Create spans for operations**: Helps visualize request flow
5. **Don't log sensitive data**: Use scrubbing patterns
6. **Log at boundaries**: Service entry/exit, external calls

## Verification

After configuration:

1. Make some API requests
2. Check Logfire dashboard (or console)
3. Verify traces show expected spans
4. Confirm sensitive data is scrubbed
