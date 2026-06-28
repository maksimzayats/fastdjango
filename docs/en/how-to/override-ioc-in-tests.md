# Override IoC in Tests

Integration tests create a fresh container per test.

Override dependencies before resolving controllers or app factories:

```python
container.add_instance(fake_dependency, provides=DependencyContract)
```

For HTTP tests, use `TestClientFactory` from `tests.integration.factories`. It resolves `FastAPIFactory` after test overrides are in place.

The integration fixture sets `DATABASE_URL` to a temporary SQLite database and runs Alembic migrations before creating the container.
