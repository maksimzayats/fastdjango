# Docker Services

| Service | Purpose |
| --- | --- |
| `api` | Production-style API process |
| `postgres` | Local PostgreSQL database |
| `pgbouncer` | PostgreSQL connection pool |
| `redis` | Rate-limiting store |

Start local dependencies:

```bash
docker compose up -d postgres redis
```

The API service waits for PgBouncer and Redis health checks before starting.
