# Docker Services

Reference for container configuration and management.

## Services Overview

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `postgres` | `postgres:17` | 5432 | Database |
| `redis` | `redis:7` | 6379 | Cache, Celery broker |
| `minio` | `minio/minio` | 9000, 9001 | Object storage (S3-compatible) |

## PostgreSQL

### Configuration

```yaml
postgres:
  image: postgres:17
  environment:
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    POSTGRES_DB: postgres
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

### Connection String

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
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
  image: redis:7
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

### Connection String

```bash
REDIS_URL=redis://localhost:6379/0
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
  image: minio/minio
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
  ports:
    - "9000:9000"  # API
    - "9001:9001"  # Console
  volumes:
    - minio_data:/data
```

### Environment Variables

```bash
AWS_S3_ACCESS_KEY_ID=minioadmin
AWS_S3_SECRET_ACCESS_KEY=minioadmin
AWS_S3_BUCKET_NAME=static
AWS_S3_ENDPOINT_URL=http://localhost:9000
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

- Username: `minioadmin`
- Password: `minioadmin`

## Init Containers

### Migrations

```yaml
migrations:
  build: .
  command: python src/manage.py migrate
  depends_on:
    - postgres
  environment:
    - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/postgres
```

Run:
```bash
docker compose up migrations
```

### Collect Static

```yaml
collectstatic:
  build: .
  command: python src/manage.py collectstatic --noinput
  depends_on:
    - minio
  environment:
    - AWS_S3_ENDPOINT_URL=http://minio:9000
```

Run:
```bash
docker compose up collectstatic
```

## Common Operations

### Start All Infrastructure

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
docker volume inspect aiogram-django-template_postgres_data
```

### Remove Volume

```bash
docker volume rm aiogram-django-template_postgres_data
```

## Network

All services connect to a shared network for inter-service communication.

```yaml
networks:
  default:
    name: fastdjango-network
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

# Or use different port
docker compose up -d postgres -p 5433:5432
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
