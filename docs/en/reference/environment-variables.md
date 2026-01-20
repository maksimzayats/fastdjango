# Environment Variables

Complete reference for all configuration options.

## Core Settings

### Application

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `local` | Deployment environment (`local`, `development`, `staging`, `production`, `test`, `ci`) |

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |

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
| `ALLOWED_HOSTS` | No | `["*"]` | Allowed host headers |
| `CSRF_TRUSTED_ORIGINS` | No | `[]` | Trusted origins for CSRF |

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
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token expiration in minutes |

Example:
```bash
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

## S3/MinIO Settings

Prefix: `AWS_S3_`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWS_S3_ACCESS_KEY_ID` | Yes* | - | S3 access key |
| `AWS_S3_SECRET_ACCESS_KEY` | Yes* | - | S3 secret key |
| `AWS_S3_BUCKET_NAME` | Yes* | - | S3 bucket name |
| `AWS_S3_ENDPOINT_URL` | Yes* | - | S3 endpoint URL |
| `AWS_S3_REGION_NAME` | No | `us-east-1` | S3 region |

*Required if using S3 storage.

Example (MinIO local):
```bash
AWS_S3_ACCESS_KEY_ID=minioadmin
AWS_S3_SECRET_ACCESS_KEY=minioadmin
AWS_S3_BUCKET_NAME=static
AWS_S3_ENDPOINT_URL=http://localhost:9000
```

## CORS Settings

Prefix: `CORS_`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ALLOW_ORIGINS` | No | `["*"]` | Allowed origins |
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

## Thread Pool Settings

Prefix: `ANYIO_`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANYIO_THREAD_LIMITER_TOKENS` | No | `40` | Max concurrent threads for sync handlers |

## Rate Limiting Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NUMBER_OF_PROXIES` | No | `0` | Number of proxies in front of app (for IP detection) |
| `IP_HEADER` | No | `x-forwarded-for` | Header containing client IP |

## Example `.env` File

```bash
# Application
ENVIRONMENT=local

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres

# Redis
REDIS_URL=redis://localhost:6379/0

# Django
DJANGO_SECRET_KEY=your-secret-key-change-in-production
DJANGO_DEBUG=true

# JWT
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# S3/MinIO
AWS_S3_ACCESS_KEY_ID=minioadmin
AWS_S3_SECRET_ACCESS_KEY=minioadmin
AWS_S3_BUCKET_NAME=static
AWS_S3_ENDPOINT_URL=http://localhost:9000

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
