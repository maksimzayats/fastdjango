# Docker Services

Reference for container configuration and management.

Docker assets live in `docker/`. The default `.env.example` sets
`COMPOSE_FILE=docker/docker-compose.yaml:docker/docker-compose.local.yaml`,
so local `docker compose` commands can still be run from the repository root
after the generated project has a local `.env`.

## Services overview

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `postgres` | `postgres:18.3-alpine` | `${POSTGRES_PORT:-5432}` | Database |
| `pgbouncer` | `edoburu/pgbouncer:v1.25.1-p0` | internal | PostgreSQL connection pool |
| `redis` | `redis:8.6.2` | `${REDIS_PORT:-6379}` | Cache, throttling, Celery broker/result backend |
| `minio` | `minio/minio:RELEASE.2025-09-07T16-13-09Z` | `${MINIO_API_PORT:-9000}`, `${MINIO_CONSOLE_PORT:-9001}` | Object storage (S3-compatible) |

## PostgreSQL

### Configuration

```yaml
postgres:
  image: postgres:18.3-alpine
  environment:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: example-postgres-password
    POSTGRES_DB: postgres
  ports:
    - "${POSTGRES_PORT:-5432}:5432"
  volumes:
    - postgres_data:/var/lib/postgresql
```

### Connection string

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
docker compose exec postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

# Stop
docker compose stop postgres
```

## Redis

### Configuration

```yaml
redis:
  image: redis:8.6.2
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

### Connection string

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
docker compose exec redis sh -c 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli'

# Monitor commands
docker compose exec redis sh -c 'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli MONITOR'

# Stop
docker compose stop redis
```

## MinIO (S3 storage)

### Configuration

```yaml
minio:
  image: minio/minio:RELEASE.2025-09-07T16-13-09Z
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: ${MINIO_ROOT_USER}
    MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
  ports:
    - "${MINIO_API_PORT:-9000}:9000"  # API
    - "${MINIO_CONSOLE_PORT:-9001}:9001"  # Console
  volumes:
    - minio_data:/data
```

### Environment variables

```bash
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
MINIO_ROOT_USER=example-minio-access-key-id
MINIO_ROOT_PASSWORD=example-minio-secret-access-key
AWS_S3_ENDPOINT_URL=http://localhost:${MINIO_API_PORT}
AWS_S3_PUBLIC_ENDPOINT_URL=http://localhost:${MINIO_API_PORT}
AWS_S3_ACCESS_KEY_ID=example-minio-access-key-id
AWS_S3_SECRET_ACCESS_KEY=example-minio-secret-access-key
AWS_S3_PUBLIC_BUCKET_NAME=public
AWS_S3_PROTECTED_BUCKET_NAME=protected
```

### Commands

```bash
# Start
docker compose up -d minio
docker compose up minio-create-buckets

# View logs
docker compose logs -f minio

# Access console
open http://localhost:9001

# Stop
docker compose stop minio
```

### Web console

Access MinIO console at http://localhost:9001

- Username: value of `MINIO_ROOT_USER`
- Password: value of `MINIO_ROOT_PASSWORD`

## Health checks

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

## Init containers

### Migrations

```yaml
migrations:
  <<: *common
  command: python management/manage.py migrate --noinput
  depends_on:
    pgbouncer:
      condition: service_healthy
```

Run:
```bash
docker compose up migrations
```

### Collect static

```yaml
collectstatic:
  <<: *common
  command: python management/manage.py collectstatic --noinput
  depends_on:
    pgbouncer:
      condition: service_healthy
    minio-create-buckets:
      condition: service_completed_successfully
```

Run:
```bash
docker compose up collectstatic
```

`AWS_S3_ENDPOINT_URL` is the internal container endpoint, while `AWS_S3_PUBLIC_ENDPOINT_URL`
must be browser-reachable for Django admin static files.

## Common operations

### Start local services

```bash
# Local Docker PostgreSQL and Redis
docker compose up -d postgres redis

# If you selected local MinIO storage
docker compose up -d minio
docker compose up minio-create-buckets
```

### Stop all services

```bash
docker compose down
```

### Reset local Docker data

```bash
docker compose down -v  # Remove volumes
docker compose up -d postgres redis

# If you selected local MinIO storage
docker compose up -d minio
docker compose up minio-create-buckets

docker compose up migrations collectstatic
```

### View all logs

```bash
docker compose logs -f
```

### Check service status

```bash
docker compose ps
```

### Restart a service

```bash
docker compose restart postgres
```

## Volumes

| Volume | Service | Purpose |
|--------|---------|---------|
| `postgres_data` | PostgreSQL | Database files |
| `redis_data` | Redis | Persistence |
| `minio_data` | MinIO | Object storage |

### Inspect volume

```bash
docker volume inspect <project>_postgres_data
```

### Remove volume

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

### Port already in use

```bash
# Find process
lsof -i :5432

# Or change the published port in docker/docker-compose.local.yaml
```

### Container won't start

```bash
# Check logs
docker compose logs postgres

# Check status
docker compose ps
```

### Database connection refused

If you selected local Docker PostgreSQL, ensure it is running and healthy:

```bash
docker compose ps postgres
docker compose logs postgres
```

### MinIO bucket not found

Run bucket creation:

```bash
docker compose up minio-create-buckets
```

### Reset to clean state

```bash
docker compose down -v
docker compose up -d postgres redis

# If you selected local MinIO storage
docker compose up -d minio
docker compose up minio-create-buckets

docker compose up migrations collectstatic
```

## Production considerations

For production deployments:

1. **Use managed services**: database, cache, and object storage providers
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
