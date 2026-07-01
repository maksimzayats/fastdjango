# Run Migrations

Create a migration after changing SQLAlchemy models:

```bash
make makemigrations
```

Review the generated file in `migrations/versions/`.

Apply migrations:

```bash
make migrate
```

For local development, start PostgreSQL first:

```bash
docker compose up -d postgres
```
