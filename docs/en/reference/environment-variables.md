# Environment Variables

Complete reference for all configuration options.

## Core Settings

### Application

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `COMPOSE_PROJECT_NAME` | No | directory name | Docker Compose project name. Generated projects usually set this from the distribution name. |
| `COMPOSE_FILE` | No | - | Compose files to load. `.env.example` uses the base and local overlay files. |
| `ENVIRONMENT` | No | `production` | Deployment environment (`local`, `development`, `staging`, `production`, `test`, `ci`). `.env.example` sets this to `local` for development. |
| `VERSION` | No | `0.1.0` | Application version used by shared settings |
| `TIME_ZONE` | No | `UTC` | Application timezone; also used by Celery |

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | Database connection string. Generated projects can use SQLite, local PostgreSQL, or remote PostgreSQL values. |
| `DATABASE_CONN_MAX_AGE` | No | `0` | Django persistent connection lifetime in seconds. Keep `0` for ASGI/FastAPI; use database/backend pooling instead. |
| `DATABASE_DISABLE_SERVER_SIDE_CURSORS` | No | `true` | Disable server-side cursors; keep `true` when using PgBouncer transaction pooling. |
| `DATABASE_DEFAULT_AUTO_FIELD` | No | `django.db.models.BigAutoField` | Default primary-key field type for Django models |
| `DATABASE_TEST_NAME` | No | - | Optional Django test database name. Use a file-backed SQLite test DB to avoid in-memory connection warnings. |
| `POSTGRES_PORT` | No | `5432` | Host port used by the local Docker PostgreSQL service |

Example:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

### Redis

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | - | Redis connection string |
| `REDIS_PASSWORD` | Yes* | - | Password enforced by the local Docker Redis container. Must match the password embedded in `REDIS_URL`. |
| `REDIS_PORT` | No | `6379` | Host port used by the local Docker Redis service |

*Required when the generated project keeps local Docker Redis.

Example:
```bash
REDIS_PASSWORD=example-redis-password
REDIS_PORT=6379
REDIS_URL=redis://default:${REDIS_PASSWORD}@localhost:${REDIS_PORT}/0
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

## Storage Settings

S3-compatible settings use the `AWS_S3_` prefix.

The runtime default is `s3` when `STORAGE_BACKEND` is omitted, but generated
projects should set an explicit value for the storage capability they keep.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STORAGE_BACKEND` | No | `s3` | `local` for filesystem storage, `s3` for MinIO or remote S3-compatible storage |
| `STATIC_URL` | No | `/static/` | URL prefix for static files |
| `STATIC_ROOT` | No | `staticfiles` | Filesystem path for collected static files in local storage mode |
| `MEDIA_URL` | No | `/media/` | URL prefix for uploaded media |
| `MEDIA_ROOT` | No | `media` | Filesystem path for uploaded files in local storage mode |
| `AWS_S3_ACCESS_KEY_ID` | Yes* | - | S3 access key |
| `AWS_S3_SECRET_ACCESS_KEY` | Yes* | - | S3 secret key |
| `AWS_S3_ENDPOINT_URL` | Yes* | - | Internal S3 endpoint used by Django and `collectstatic` (for Docker: `http://minio:9000`) |
| `AWS_S3_PUBLIC_ENDPOINT_URL` | No | - | Browser-reachable endpoint used to generate public static URLs (for Docker: `http://localhost:9000`) |
| `AWS_S3_REGION_NAME` | No | - | S3 region name |
| `AWS_S3_PUBLIC_BUCKET_NAME` | No | `public` | Public bucket name used by Django staticfiles storage |
| `AWS_S3_PROTECTED_BUCKET_NAME` | No | `protected` | Private bucket name used by default Django file storage |
| `MINIO_API_PORT` | No | `9000` | Host port used by the local MinIO API |
| `MINIO_CONSOLE_PORT` | No | `9001` | Host port used by the local MinIO console |
| `MINIO_ROOT_USER` | No | - | Local MinIO root user; generated to match `AWS_S3_ACCESS_KEY_ID` |
| `MINIO_ROOT_PASSWORD` | No | - | Local MinIO root password; generated to match `AWS_S3_SECRET_ACCESS_KEY` |

*The `AWS_S3_*` credential and endpoint values are required when `STORAGE_BACKEND=s3`.
`MINIO_ROOT_*` is only used by the local MinIO service.

Example (local filesystem):
```bash
STORAGE_BACKEND=local
```

Example (MinIO local):
```bash
STORAGE_BACKEND=s3
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
MINIO_ROOT_USER=example-minio-access-key-id
MINIO_ROOT_PASSWORD=example-minio-secret-access-key
AWS_S3_ENDPOINT_URL=http://localhost:${MINIO_API_PORT}
AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:${MINIO_API_PORT}
AWS_S3_ACCESS_KEY_ID=example-minio-access-key-id
AWS_S3_SECRET_ACCESS_KEY=example-minio-secret-access-key
AWS_S3_REGION_NAME=us-east-1
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
| `LOGFIRE_SERVICE_NAME` | No | `modern-python-template` | Service name reported to Logfire |
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

This example matches local Docker PostgreSQL, local Docker Redis, and local
MinIO storage. A generated project may have a shorter file when the prompt keeps
SQLite, remote services, or local filesystem storage.

```bash
# Compose
COMPOSE_PROJECT_NAME=modern-python-template
COMPOSE_FILE=docker/docker-compose.yaml:docker/docker-compose.local.yaml

# Application
DJANGO_DEBUG=true
ENVIRONMENT=local
LOGGING_LEVEL=DEBUG

# Secrets
DJANGO_SECRET_KEY=example-django-secret-key
JWT_SECRET_KEY=example-jwt-secret-key-with-at-least-32-bytes

# HTTP
ALLOWED_HOSTS=["127.0.0.1","localhost","0.0.0.0"]
CSRF_TRUSTED_ORIGINS=["http://localhost"]
CORS_ALLOW_ORIGINS=["http://localhost"]

# Observability
LOGFIRE_ENABLED=false
LOGFIRE_SERVICE_NAME=modern-python-template
LOGFIRE_ENVIRONMENT=local

# Database
POSTGRES_DB=postgres
POSTGRES_PASSWORD=example-postgres-password
POSTGRES_PORT=5432
POSTGRES_USER=postgres
DATABASE_URL="postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"

# Redis
REDIS_PASSWORD=example-redis-password
REDIS_PORT=6379
REDIS_URL="redis://default:${REDIS_PASSWORD}@localhost:${REDIS_PORT}/0"

# Storage
STORAGE_BACKEND=s3
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
MINIO_ROOT_USER=example-minio-access-key-id
MINIO_ROOT_PASSWORD=example-minio-secret-access-key

# S3
AWS_S3_ENDPOINT_URL=http://localhost:${MINIO_API_PORT}
AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:${MINIO_API_PORT}
AWS_S3_ACCESS_KEY_ID=example-minio-access-key-id
AWS_S3_SECRET_ACCESS_KEY=example-minio-secret-access-key
AWS_S3_REGION_NAME=us-east-1
AWS_S3_PUBLIC_BUCKET_NAME=public
AWS_S3_PROTECTED_BUCKET_NAME=protected
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
