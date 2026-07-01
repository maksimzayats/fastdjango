# Settings

Runtime configuration is modeled with `pydantic-settings` classes near the classes that consume them.

Important settings include:

- `DATABASE_URL` for SQLAlchemy.
- `JWT_SECRET_KEY` for access-token signing.
- `REDIS_URL` for rate limiting.
- `ALLOWED_HOSTS` for trusted-host middleware.
- `CORS_ALLOW_ORIGINS` for browser clients.
- `TRUST_FORWARDED_IP_HEADER` for proxy IP handling; keep it `false` unless the app is behind trusted proxy infrastructure.
- `LOGFIRE_*` for optional telemetry.

Do not read environment variables inside use cases or services. Inject a focused settings object instead.
