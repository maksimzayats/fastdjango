# Override IoC in Tests

Integration tests create a fresh container per test.

Override dependencies before resolving controllers or app factories:

```python
container.add_instance(fake_dependency, provides=DependencyContract)
```

For HTTP tests, use `TestClientFactory` from `tests.integration.factories`. It resolves `FastAPIFactory` after test overrides are in place.

The integration fixture sets `DATABASE_URL` to a temporary SQLite database and runs Alembic migrations before creating the container.

Use the provided factory fixtures instead of constructing them inside tests:

```python
def test_health(test_client_factory: TestClientFactory) -> None:
    with test_client_factory() as test_client:
        response = test_client.get("/api/v1/health")
```

Delivery integration tests should not import SQLAlchemy models, sessions, or adapters. Prepare database state through test factories that use the unit of work and repositories:

```python
inactive_user = user_factory(username="inactive_user", is_active=False)
refresh_token = refresh_session_factory(user=inactive_user)
```

Unit tests are different: they may instantiate the subject directly with deterministic fakes when that makes the behavior under test clear.
