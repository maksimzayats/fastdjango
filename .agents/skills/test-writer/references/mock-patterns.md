# Mock Patterns

## Basic Pattern

```python
from unittest.mock import MagicMock

import pytest

from fastdjango.core.product.services import ProductService
from tests.integration.factories import TestClientFactory


@pytest.mark.django_db(transaction=True)
def test_with_mocked_service(container: Container) -> None:
    mock_service = MagicMock(spec=ProductService)
    mock_service.list_products.return_value = []

    container.add_instance(mock_service, provides=ProductService)

    test_client_factory = TestClientFactory(container=container)
    with test_client_factory() as client:
        response = client.get("/v1/products")

    assert response.status_code == HTTPStatus.OK
    mock_service.list_products.assert_called_once()
```

## Rules

- Use `MagicMock(spec=RealClass)`.
- Override with `container.add_instance(mock, provides=RealClass)`.
- Override before resolving a factory, controller, use case, or service that depends on it.
- Prefer integration tests for HTTP behavior and unit tests for reusable business logic.

## Common Assertions

```python
mock_service.create.assert_called_once()
mock_service.update.assert_called_with(product_id=1, name="Updated")
mock_service.delete.assert_not_called()
```

## Too Late

```python
test_client_factory = TestClientFactory(container=container)
container.add_instance(mock_service, provides=ProductService)
```

The factory or its dependencies may already be resolved. Register the override first.
