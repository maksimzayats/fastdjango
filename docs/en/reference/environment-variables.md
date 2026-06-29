# Environment Variables

| Name | Required | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` | No | Runtime environment name such as `local`, `test`, or `production` |
| `VERSION` | No | Application version exposed through runtime settings |
| `TIME_ZONE` | No | Default application timezone name |
| `LOGGING_LEVEL` | No | Logging threshold |
| `JWT_SECRET_KEY` | Yes | Secret used to sign access tokens |
| `JWT_ALGORITHM` | No | Signing algorithm used for access tokens |
| `JWT_TYP` | No | JWT `typ` claim value used for issued access tokens |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | Access-token lifetime in minutes |
| `REFRESH_SESSION_REFRESH_TOKEN_NBYTES` | No | Number of random bytes used before URL-safe encoding refresh tokens |
| `REFRESH_SESSION_REFRESH_TOKEN_TTL_DAYS` | No | Number of days before a refresh session expires |
| `PASSWORD_MIN_LENGTH` | No | Minimum accepted password length |
| `PASSWORD_MAX_LENGTH` | No | Maximum accepted password length |
| `DATABASE_URL` | No | Database URL; defaults to local SQLite when omitted |
| `DATABASE_ECHO` | No | Enables SQLAlchemy SQL echo logging when `true` |
| `REDIS_URL` | Yes | Redis URL used by rate limiting |
| `ALLOWED_HOSTS` | No | Trusted host middleware values |
| `CORS_ALLOW_CREDENTIALS` | No | Whether CORS responses allow browser credentials |
| `CORS_ALLOW_HEADERS` | No | Headers accepted by CORS middleware |
| `CORS_ALLOW_METHODS` | No | HTTP methods accepted by CORS middleware |
| `CORS_ALLOW_ORIGINS` | No | Browser origins allowed by CORS middleware |
| `TRUST_FORWARDED_IP_HEADER` | No | Trusts `X-Forwarded-For` for client identity; keep `false` unless the app is behind trusted proxy infrastructure |
| `IP_HEADER` | No | Header used to read the forwarded client IP trace when trusted |
| `USER_AGENT_HEADER` | No | Header used to read the user agent for token sessions |
| `LOGFIRE_ENABLED` | No | Enables Logfire telemetry when `true` |
| `LOGFIRE_ENVIRONMENT` | No | Environment label attached to Logfire telemetry |
| `LOGFIRE_SERVICE_NAME` | No | Service name attached to Logfire telemetry |
| `LOGFIRE_SERVICE_VERSION` | No | Service version attached to Logfire telemetry |
| `LOGFIRE_TOKEN` | When enabled | Logfire write token |
| `INSTRUMENTOR_FASTAPI_EXCLUDED_URLS` | No | URL patterns excluded from FastAPI request instrumentation |

PostgreSQL URLs can use `postgres://...` or `postgresql://...`; runtime settings convert them to the async SQLAlchemy driver URL.
