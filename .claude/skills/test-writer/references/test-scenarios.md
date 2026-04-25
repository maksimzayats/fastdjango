# Test Scenarios

## Authenticated Endpoint

```python
with test_client_factory(auth_for_user=user) as client:
    response = client.get("/v1/users/me")

assert response.status_code == HTTPStatus.OK
```

## Unauthenticated Endpoint

```python
with test_client_factory() as client:
    response = client.get("/v1/users/me")

assert response.status_code == HTTPStatus.FORBIDDEN
```

## Not Found

```python
with test_client_factory(auth_for_user=user) as client:
    response = client.get("/v1/items/99999")

assert response.status_code == HTTPStatus.NOT_FOUND
```

## Validation Error

```python
with test_client_factory(auth_for_user=user) as client:
    response = client.post("/v1/items", json={})

assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
```

## Celery Task

```python
registry = tasks_registry_factory()

with celery_worker_factory():
    result = registry.ping.delay().get(timeout=10)

assert result == {"result": "pong"}
```

## Unit Test for a Service

```python
def test_service_rule(service: ProductService) -> None:
    result = service.calculate_total(...)
    assert result == expected
```

Keep unit tests focused on behavior that belongs to the template or reusable domain logic.
