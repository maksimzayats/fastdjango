# Docker Services

Reference for container configuration and management.

Docker assets live in `docker/`. The default `.env.example` sets
`COMPOSE_FILE=docker/docker-compose.yaml:docker/docker-compose.local.yaml`,
so local `docker compose` commands can still be run from the repository root
after copying `.env.example` to `.env`.

## Services Overview

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `postgres` | `postgres:18-alpine` | `${POSTGRES_PORT:-5432}` | Database |
| `pgbouncer` | `edoburu/pgbouncer` | internal | PostgreSQL connection pool |
| `redis` | `redis:latest` | `${REDIS_PORT:-6379}` | Cache, throttling, Celery broker/result backend |
| `minio` | `minio/minio:latest` | `${MINIO_API_PORT:-9000}`, `${MINIO_CONSOLE_PORT:-9001}` | Object storage (S3-compatible) |

## PostgreSQL

### Configuration

```yaml
postgres:
  image: postgres:18-alpine
  environment:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: example-postgres-password
    POSTGRES_DB: postgres
  ports:
    - "${POSTGRES_PORT:-5432}:5432"
  volumes:
    - postgres_data:/var/lib/postgresql
```

### Connection String

```bash
DATABASE_URL=postgres://postgres:example-postgres-password@localhost:${POSTGRES_PORT:-5432}/postgres
```

Containers connect through PgBouncer by default:

```bash
DATABASE_URL=postgres://postgres:example-postgres-password@pgbouncer:5432/postgres
```

### Commands

```bash
# Start
docker compose up -d postgres

# View logs
docker compose logs -f postgres

# Connect with psql
docker compose exec postgres psql -U postgres

# Stop
docker compose stop postgres
```

## Redis

### Configuration

```yaml
redis:
  image: redis:latest
  command:
    - redis-server
    - --requirepass
    - ${REDIS_PASSWORD}
  ports:
    - "${REDIS_PORT:-6379}:6379"
  volumes:
    - redis_data:/data
  healthcheck:
    test: ["CMD-SHELL", "REDISCLI_AUTH=\"$${REDIS_PASSWORD}\" redis-cli ping | grep PONG"]
```

### Connection String

```bash
REDIS_URL=redis://default:${REDIS_PASSWORD}@localhost:${REDIS_PORT:-6379}/0
```

### Commands

```bash
# Start
docker compose up -d redis

# View logs
docker compose logs -f redis

# Connect with redis-cli
docker compose exec redis redis-cli

# Monitor commands
docker compose exec redis redis-cli MONITOR

# Stop
docker compose stop redis
```

## MinIO (S3 Storage)

### Configuration

```yaml
minio:
  image: minio/minio:latest
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: ${AWS_S3_ACCESS_KEY_ID}
    MINIO_ROOT_PASSWORD: ${AWS_S3_SECRET_ACCESS_KEY}
  ports:
    - "${MINIO_API_PORT:-9000}:9000"  # API
    - "${MINIO_CONSOLE_PORT:-9001}:9001"  # Console
  volumes:
    - minio_data:/data
```

### Environment Variables

```bash
AWS_S3_ACCESS_KEY_ID=example-minio-access-key-id
AWS_S3_SECRET_ACCESS_KEY=example-minio-secret-access-key
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
AWS_S3_ENDPOINT_URL=http://localhost:9000
AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:9000
AWS_S3_PUBLIC_BUCKET_NAME=public
AWS_S3_PROTECTED_BUCKET_NAME=protected
```

### Commands

```bash
# Start
docker compose up -d minio minio-create-buckets

# View logs
docker compose logs -f minio

# Access console
open http://localhost:9001

# Stop
docker compose stop minio
```

### Web Console

Access MinIO console at http://localhost:9001

- Username: value of `AWS_S3_ACCESS_KEY_ID`
- Password: value of `AWS_S3_SECRET_ACCESS_KEY`

## Health Checks

The `api` service healthcheck calls the existing HTTP health endpoint:

```yaml
api:
  healthcheck:
    test:
      - CMD
      - python
      - -c
      - "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/v1/health', timeout=8).read()"
```

`GET /v1/health` checks database connectivity, enqueues the built-in Celery
`ping` task with `.adelay()`, waits for the worker result, and forgets the
result after it is read. This keeps Docker health aligned with the real HTTP
readiness contract instead of adding a second Celery-only health entrypoint.

## Init Containers

### Migrations

```yaml
migrations:
  build: .
  command: python management/manage.py migrate --noinput
  depends_on:
    - pgbouncer
  environment:
    - DATABASE_URL=postgres://postgres:example-postgres-password@pgbouncer:5432/postgres
```

Run:
```bash
docker compose up migrations
```

### Collect Static

```yaml
collectstatic:
  build: .
  command: python management/manage.py collectstatic --noinput
  depends_on:
    - minio-create-buckets
  environment:
    - AWS_S3_ENDPOINT_URL=http://minio:9000
    - AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:9000
```

Run:
```bash
docker compose up collectstatic
```

`AWS_S3_ENDPOINT_URL` is the internal container endpoint, while `AWS_S3_PUBLIC_ENDPOINT_URL`
must be browser-reachable for Django admin static files.

## Common Operations

### Start Core Local Services

```bash
docker compose up -d postgres redis minio minio-create-buckets
```

### Stop All Services

```bash
docker compose down
```

### Reset Everything (Including Data)

```bash
docker compose down -v  # Remove volumes
docker compose up -d postgres redis minio minio-create-buckets
docker compose up migrations
```

### View All Logs

```bash
docker compose logs -f
```

### Check Service Status

```bash
docker compose ps
```

### Restart a Service

```bash
docker compose restart postgres
```

## Volumes

| Volume | Service | Purpose |
|--------|---------|---------|
| `postgres_data` | PostgreSQL | Database files |
| `redis_data` | Redis | Persistence |
| `minio_data` | MinIO | Object storage |

### Inspect Volume

```bash
docker volume inspect <project>_postgres_data
```

### Remove Volume

```bash
docker volume rm <project>_postgres_data
```

## Network

All services connect to the default Compose network for inter-service communication.

```yaml
networks:
  main:
    driver: bridge
```

Internal hostnames:

- `postgres` - Database
- `redis` - Cache
- `minio` - Object storage

## Troubleshooting

### Port Already in Use

```bash
# Find process
lsof -i :5432

# Or change the published port in docker/docker-compose.local.yaml
```

### Container Won't Start

```bash
# Check logs
docker compose logs postgres

# Check status
docker compose ps
```

### Database Connection Refused

Ensure postgres is running and healthy:

```bash
docker compose ps postgres
docker compose logs postgres
```

### MinIO Bucket Not Found

Run bucket creation:

```bash
docker compose up minio-create-buckets
```

### Reset to Clean State

```bash
docker compose down -v
docker compose up -d postgres redis minio minio-create-buckets
docker compose up migrations collectstatic
```

## Production Considerations

For production deployments:

1. **Use managed services**: AWS RDS, ElastiCache, S3
2. **Set strong passwords**: Don't use defaults
3. **Enable persistence**: Configure backup strategies
4. **Use health checks**: Add to compose file
5. **Set resource limits**: Memory and CPU limits

Example health check:

```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U postgres"]
    interval: 10s
    timeout: 5s
    retries: 5
```
