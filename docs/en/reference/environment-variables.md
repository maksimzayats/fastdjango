# Environment Variables

Complete reference for all configuration options.

## Core Settings

### Application

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `production` | Deployment environment (`local`, `development`, `staging`, `production`, `test`, `ci`). `.env.example` sets this to `local` for development. |
| `VERSION` | No | `0.1.0` | Application version used by shared settings |
| `TIME_ZONE` | No | `UTC` | Application timezone; also used by Celery |

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `DATABASE_CONN_MAX_AGE` | No | `600` | Django persistent connection lifetime in seconds |
| `DATABASE_DEFAULT_AUTO_FIELD` | No | `django.db.models.BigAutoField` | Default primary-key field type for Django models |

Example:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### Redis

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | - | Redis connection string |

Example:
```bash
REDIS_URL=redis://localhost:6379/0
```

## Django Settings

Prefix: `DJANGO_`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | Yes | - | Django secret key for cryptographic signing |
| `DJANGO_DEBUG` | No | `false` | Enable debug mode |

### HTTP Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALLOWED_HOSTS` | No | `["localhost", "127.0.0.1"]` | Allowed host headers for Django and FastAPI trusted-host middleware |
| `CSRF_TRUSTED_ORIGINS` | No | `["http://localhost"]` | Trusted origins for CSRF |

Example:
```bash
ALLOWED_HOSTS=["localhost","127.0.0.1","example.com"]
CSRF_TRUSTED_ORIGINS=["https://example.com"]
```

## JWT Settings

Prefix: `JWT_`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | Yes | - | Secret key for signing tokens |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_TYP` | No | `at+jwt` | JWT `typ` claim for access tokens |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Access token expiration in minutes |

Example:
```bash
JWT_SECRET_KEY=your-super-secret-jwt-key-with-at-least-32-bytes
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

## S3/MinIO Settings

Prefix: `AWS_S3_`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STATIC_URL` | No | `/static/` | URL prefix for static files |
| `MEDIA_URL` | No | `/media/` | URL prefix for uploaded media |
| `AWS_S3_ACCESS_KEY_ID` | Yes* | - | S3 access key |
| `AWS_S3_SECRET_ACCESS_KEY` | Yes* | - | S3 secret key |
| `AWS_S3_ENDPOINT_URL` | Yes* | - | Internal S3 endpoint used by Django and `collectstatic` (for Docker: `http://minio:9000`) |
| `AWS_S3_PUBLIC_ENDPOINT_URL` | No | - | Browser-reachable endpoint used to generate public static URLs (for Docker: `http://localhost:9000`) |
| `AWS_S3_PUBLIC_BUCKET_NAME` | No | `public` | Public bucket name used by Django staticfiles storage |
| `AWS_S3_PROTECTED_BUCKET_NAME` | No | `protected` | Private bucket name used by default Django file storage |

*Required if using S3 storage.

Example (MinIO local):
```bash
AWS_S3_ACCESS_KEY_ID=example-minio-access-key-id
AWS_S3_SECRET_ACCESS_KEY=example-minio-secret-access-key
AWS_S3_ENDPOINT_URL=http://minio:9000
AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:9000
AWS_S3_PUBLIC_BUCKET_NAME=public
AWS_S3_PROTECTED_BUCKET_NAME=protected
```

## CORS Settings

Prefix: `CORS_`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ALLOW_ORIGINS` | No | `["http://localhost"]` | Allowed origins |
| `CORS_ALLOW_METHODS` | No | `["*"]` | Allowed HTTP methods |
| `CORS_ALLOW_HEADERS` | No | `["*"]` | Allowed headers |
| `CORS_ALLOW_CREDENTIALS` | No | `true` | Allow credentials |

Example:
```bash
CORS_ALLOW_ORIGINS=["https://app.example.com","https://admin.example.com"]
CORS_ALLOW_METHODS=["GET","POST","PUT","DELETE"]
```

## Logging Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOGGING_LEVEL` | No | `INFO` | Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## Logfire/OpenTelemetry Settings

Prefix: `LOGFIRE_`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOGFIRE_ENABLED` | No | `false` | Enable Logfire instrumentation |
| `LOGFIRE_TOKEN` | No | - | Logfire authentication token |
| `LOGFIRE_SERVICE_NAME` | No | `fastdjango` | Service name reported to Logfire |
| `LOGFIRE_SERVICE_VERSION` | No | `0.1.0` | Service version reported to Logfire |
| `LOGFIRE_ENVIRONMENT` | No | `production` | Environment name reported to Logfire |

## Instrumentation Settings

Prefix: `INSTRUMENTOR_`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `INSTRUMENTOR_FASTAPI_EXCLUDED_URLS` | No | `[".*/v1/health"]` | FastAPI URL patterns excluded from tracing |

## Thread Pool Settings

Prefix: `ANYIO_`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANYIO_THREAD_LIMITER_TOKENS` | No | `40` | Max concurrent threads for sync handlers |

## Celery Settings

Prefix: `CELERY_`

Most projects only need `REDIS_URL` for local development. Tune these when you
need different worker, retry, or serialization behavior.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CELERY_WORKER_PREFETCH_MULTIPLIER` | No | `1` | Number of tasks a worker prefetches |
| `CELERY_WORKER_MAX_TASKS_PER_CHILD` | No | `1000` | Restart worker child after this many tasks |
| `CELERY_WORKER_MAX_MEMORY_PER_CHILD` | No | - | Optional worker child memory limit in KB |
| `CELERY_TASK_ACKS_LATE` | No | `true` | Acknowledge tasks after execution |
| `CELERY_TASK_REJECT_ON_WORKER_LOST` | No | `true` | Requeue tasks if a worker process is lost |
| `CELERY_TASK_TIME_LIMIT` | No | `300` | Hard task time limit in seconds |
| `CELERY_TASK_SOFT_TIME_LIMIT` | No | `270` | Soft task time limit in seconds |
| `CELERY_RESULT_EXPIRES` | No | `3600` | Result expiration in seconds |
| `CELERY_RESULT_BACKEND_ALWAYS_RETRY` | No | `true` | Retry result backend operations on transient errors |
| `CELERY_RESULT_BACKEND_MAX_RETRIES` | No | `10` | Maximum result backend retries |
| `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP` | No | `true` | Retry broker connection on worker startup |
| `CELERY_BROKER_CONNECTION_MAX_RETRIES` | No | `10` | Maximum broker connection retries; empty means unlimited |
| `CELERY_TASK_SERIALIZER` | No | `json` | Task serialization format |
| `CELERY_RESULT_SERIALIZER` | No | `json` | Result serialization format |
| `CELERY_ACCEPT_CONTENT` | No | `["json"]` | Accepted content types |
| `CELERY_WORKER_SEND_TASK_EVENTS` | No | `true` | Emit worker task events for monitoring |
| `CELERY_TASK_SEND_SENT_EVENT` | No | `true` | Emit task-sent events |

## Rate Limiting Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `IP_HEADER` | No | `x-forwarded-for` | Header containing the forwarded IP address trace |
| `USER_AGENT_HEADER` | No | `user-agent` | Header containing the user agent |

`IP_HEADER` is used whenever present. In production, expose the application through a
trusted proxy before relying on client-controlled forwarded headers.

## Refresh Session Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REFRESH_TOKEN_NBYTES` | No | `32` | Random byte length used when issuing refresh tokens |
| `REFRESH_TOKEN_TTL_DAYS` | No | `30` | Refresh token lifetime in days |

## Example `.env` File

```bash
# Application
ENVIRONMENT=local

# Database
DATABASE_URL=postgres://postgres:example-postgres-password@localhost:5432/postgres

# Redis
REDIS_URL=redis://localhost:6379/0

# Django
DJANGO_SECRET_KEY=your-secret-key-change-in-production
DJANGO_DEBUG=true

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-with-at-least-32-bytes
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

# S3/MinIO
AWS_S3_ACCESS_KEY_ID=example-minio-access-key-id
AWS_S3_SECRET_ACCESS_KEY=example-minio-secret-access-key
AWS_S3_ENDPOINT_URL=http://minio:9000
AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:9000
AWS_S3_PUBLIC_BUCKET_NAME=public
AWS_S3_PROTECTED_BUCKET_NAME=protected

# CORS
CORS_ALLOW_ORIGINS=["http://localhost:3000"]

# Logging
LOGGING_LEVEL=DEBUG

# Observability
LOGFIRE_ENABLED=false
```

## Environment-Specific Examples

### Development

```bash
ENVIRONMENT=development
DJANGO_DEBUG=true
LOGGING_LEVEL=DEBUG
LOGFIRE_ENABLED=false
```

### Staging

```bash
ENVIRONMENT=staging
DJANGO_DEBUG=false
LOGGING_LEVEL=INFO
LOGFIRE_ENABLED=true
LOGFIRE_TOKEN=staging-token
```

### Production

```bash
ENVIRONMENT=production
DJANGO_DEBUG=false
LOGGING_LEVEL=WARNING
LOGFIRE_ENABLED=true
LOGFIRE_TOKEN=production-token
ALLOWED_HOSTS=["api.example.com"]
CORS_ALLOW_ORIGINS=["https://app.example.com"]
```

## Loading Order

1. `.env` file is loaded via `python-dotenv`
2. Environment variables override `.env` values
3. Pydantic Settings validate and parse values

## Type Coercion

Pydantic automatically converts:

| Type | Example |
|------|---------|
| `str` | `VALUE=hello` → `"hello"` |
| `int` | `VALUE=42` → `42` |
| `bool` | `VALUE=true` → `True` |
| `list[str]` | `VALUE=["a","b"]` → `["a", "b"]` |
| `SecretStr` | `VALUE=secret` → `SecretStr("secret")` |
