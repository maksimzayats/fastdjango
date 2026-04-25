# Testing New Features

## Test Layout

```
tests/
├── integration/
│   ├── fastapi/
│   └── celery/
└── unit/
    ├── core/
    └── infrastructure/
```

## Test Factories

Shared factories live in `tests/integration/factories.py`:

- `TestClientFactory`
- `TestUserFactory`
- `TestCeleryWorkerFactory`
- `TestTasksRegistryFactory`

Add domain-specific factories only when they make tests clearer.

## FastAPI Integration Pattern

```python
@pytest.mark.django_db(transaction=True)
def test_create_product(
    test_client_factory: TestClientFactory,
    user: User,
) -> None:
    with test_client_factory(auth_for_user=user) as client:
        response = client.post(
            "/v1/products",
            json={"name": "New Product", "price": "19.99"},
        )

    assert response.status_code == HTTPStatus.CREATED
```

## Override Pattern

```python
mock_service = MagicMock(spec=ProductService)
container.add_instance(mock_service, provides=ProductService)

test_client_factory = TestClientFactory(container=container)
```

Register overrides before resolving the factory or client that depends on them.

## Celery Pattern

```python
registry = tasks_registry_factory()

with celery_worker_factory():
    result = registry.ping.delay().get(timeout=10)

assert result == {"result": "pong"}
```

Use the project registry instead of hardcoding task names in tests.
