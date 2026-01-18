# Configure Observability

This guide explains how to set up observability with Logfire (default) or replace it with other OpenTelemetry-compatible backends.

## Default Logfire Setup

The template includes built-in support for [Logfire](https://pydantic.dev/logfire), a Pydantic-native observability platform.

### Enable Logfire

1. Create a Logfire account at [logfire.pydantic.dev](https://logfire.pydantic.dev)

2. Get your project token from the Logfire dashboard

3. Add environment variables to your `.env` file:

```bash
LOGFIRE_ENABLED=true
LOGFIRE_TOKEN=your-logfire-token-here
```

### What Gets Instrumented

When Logfire is enabled, these libraries are automatically instrumented:

- **Django** - HTTP requests and responses (excluding health checks)
- **Celery** - Task execution with trace context propagation
- **psycopg** - PostgreSQL queries with SQL comments
- **Redis** - Redis commands
- **requests** - Outbound HTTP requests
- **httpx** - Async HTTP requests
- **Pydantic** - Validation timing

The configuration is in `src/infrastructure/otel/logfire.py`:

```python
def _instrument_libraries() -> None:
    logfire.instrument_django(
        excluded_urls=".*/v1/health",
        is_sql_commentor_enabled=True,
    )
    logfire.instrument_celery(propagate_trace_context=True)
    logfire.instrument_requests()
    logfire.instrument_psycopg(
        enable_commenter=True,
        commenter_options=CommenterOptions(
            db_driver=True,
            dbapi_level=True,
        ),
    )
    logfire.instrument_httpx()
    logfire.instrument_redis()
    logfire.instrument_pydantic()
```

### Sensitive Data Scrubbing

Logfire automatically scrubs sensitive fields. Additional patterns are configured:

```python
logfire.configure(
    # ...
    scrubbing=ScrubbingOptions(
        extra_patterns=[
            "access_token",
            "refresh_token",
        ],
    ),
)
```

## Replacing Logfire with Other Backends

To use a different OpenTelemetry backend (Jaeger, Honeycomb, Datadog, etc.), replace the Logfire configuration with the OpenTelemetry SDK.

### Step 1: Install OpenTelemetry Packages

```bash
uv add opentelemetry-sdk opentelemetry-exporter-otlp
uv add opentelemetry-instrumentation-django
uv add opentelemetry-instrumentation-celery
uv add opentelemetry-instrumentation-redis
uv add opentelemetry-instrumentation-psycopg
uv add opentelemetry-instrumentation-requests
```

### Step 2: Create OpenTelemetry Configuration

Replace `src/infrastructure/otel/logfire.py` with a new file `src/infrastructure/otel/opentelemetry.py`:

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from infrastructure.configs.types import Environment


class OpenTelemetrySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OTEL_")

    enabled: bool = False
    endpoint: str = "http://localhost:4317"
    api_key: SecretStr | None = None


def configure_opentelemetry(
        service_name: str,
        environment: Environment,
        version: str,
) -> None:
    settings = OpenTelemetrySettings()
    if not settings.enabled:
        return

    resource = Resource.create({
        "service.name": service_name,
        "service.version": version,
        "deployment.environment": environment,
    })

    provider = TracerProvider(resource=resource)

    # Configure exporter with optional API key
    headers = {}
    if settings.api_key:
        # Format depends on backend (Honeycomb, Datadog, etc.)
        headers["x-honeycomb-team"] = settings.api_key.get_secret_value()

    exporter = OTLPSpanExporter(
        endpoint=settings.endpoint,
        headers=headers,
    )

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    _instrument_libraries()


def _instrument_libraries() -> None:
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor

    DjangoInstrumentor().instrument()
    CeleryInstrumentor().instrument()
    PsycopgInstrumentor().instrument()
    RedisInstrumentor().instrument()
    RequestsInstrumentor().instrument()
```

### Step 3: Update Infrastructure Configuration

Edit `src/core/configs/infrastructure.py`:

```python
# Replace this import:
# from infrastructure.otel.logfire import configure_logfire

# With this:
from infrastructure.otel.opentelemetry import configure_opentelemetry


def configure_infrastructure(service_name: str) -> None:
    # ... existing code ...

    # Replace configure_logfire with:
    configure_opentelemetry(
        service_name=service_name,
        environment=application_settings.environment,
        version=application_settings.version,
    )
```

### Step 4: Configure Environment Variables

For different backends:

**Jaeger:**
```bash
OTEL_ENABLED=true
OTEL_ENDPOINT=http://localhost:4317
```

**Honeycomb:**
```bash
OTEL_ENABLED=true
OTEL_ENDPOINT=https://api.honeycomb.io:443
OTEL_API_KEY=your-honeycomb-api-key
```

**Datadog:**
```bash
OTEL_ENABLED=true
OTEL_ENDPOINT=http://localhost:4317
# Datadog Agent handles the rest
```

**Grafana Tempo:**
```bash
OTEL_ENABLED=true
OTEL_ENDPOINT=http://tempo:4317
```

## Custom Instrumentation

### Adding Custom Spans

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class PaymentService:
    def process_payment(self, amount: float) -> dict:
        with tracer.start_as_current_span("process_payment") as span:
            span.set_attribute("payment.amount", amount)

            result = self._call_payment_gateway(amount)

            span.set_attribute("payment.status", result["status"])
            return result
```

### Adding Custom Attributes

```python
from opentelemetry import trace


def my_endpoint(request: HttpRequest) -> Response:
    span = trace.get_current_span()
    span.set_attribute("user.id", request.user.id)
    span.set_attribute("request.path", request.path)
    # ... rest of handler
```

### Recording Exceptions

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


def risky_operation() -> None:
    span = trace.get_current_span()
    try:
        # ... operation that might fail
        pass
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        raise
```

## Disabling Observability in Tests

The template automatically disables Logfire in tests via `.env.test`:

```bash
LOGFIRE_ENABLED=false
```

For custom OpenTelemetry setup:

```bash
OTEL_ENABLED=false
```

## Summary

| Backend | Environment Variables |
|---------|----------------------|
| Logfire (default) | `LOGFIRE_ENABLED`, `LOGFIRE_TOKEN` |
| Jaeger | `OTEL_ENABLED`, `OTEL_ENDPOINT` |
| Honeycomb | `OTEL_ENABLED`, `OTEL_ENDPOINT`, `OTEL_API_KEY` |
| Datadog | `OTEL_ENABLED`, `OTEL_ENDPOINT` (via Agent) |
| Grafana Tempo | `OTEL_ENABLED`, `OTEL_ENDPOINT` |

The default Logfire integration provides:

- Zero-config setup with just token
- Automatic library instrumentation
- Sensitive data scrubbing
- Pydantic-native validation insights

For custom backends, replace the Logfire module with OpenTelemetry SDK configuration.
