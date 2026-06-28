# Settings

Runtime configuration is modeled with `pydantic-settings` classes near the classes that consume them.

Important settings include:

- `DATABASE_URL` for SQLAlchemy.
- `JWT_SECRET_KEY` for access-token signing.
- `REDIS_URL` for rate limiting.
- `ALLOWED_HOSTS` for trusted-host middleware.
- `CORS_ALLOW_ORIGINS` for browser clients.
- `LOGFIRE_*` for optional telemetry.

Do not read environment variables inside use cases or services. Inject a focused settings object instead.
