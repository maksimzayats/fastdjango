# Environment Variables

| Name | Required | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` | No | Runtime environment name such as `local`, `test`, or `production` |
| `LOGGING_LEVEL` | No | Logging threshold |
| `JWT_SECRET_KEY` | Yes | Secret used to sign access tokens |
| `DATABASE_URL` | No | Database URL; defaults to local SQLite when omitted |
| `REDIS_URL` | Yes | Redis URL used by rate limiting |
| `ALLOWED_HOSTS` | No | Trusted host middleware values |
| `CORS_ALLOW_ORIGINS` | No | Browser origins allowed by CORS middleware |
| `LOGFIRE_ENABLED` | No | Enables Logfire telemetry when `true` |
| `LOGFIRE_TOKEN` | When enabled | Logfire write token |

PostgreSQL URLs can use `postgres://...` or `postgresql://...`; runtime settings convert them to the async SQLAlchemy driver URL.
