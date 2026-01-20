# Mock Patterns Reference

This reference provides comprehensive mocking patterns for testing with IoC container overrides.

## Contents

- [Basic Mocking Pattern](#basic-mocking-pattern)
- [Mock Configuration Patterns](#mock-configuration-patterns)
- [Mock Assertion Patterns](#mock-assertion-patterns)
- [Service-Specific Mock Examples](#service-specific-mock-examples)
- [Testing Multiple Services](#testing-multiple-services)
- [Mocking External Dependencies](#mocking-external-dependencies)
- [Common Pitfalls](#common-pitfalls)

## Basic Mocking Pattern

### Step-by-Step Process

```python
from unittest.mock import MagicMock

import pytest

from core.product.services import ProductService, ProductNotFoundError
from infrastructure.frameworks.punq import AutoRegisteringContainer
from tests.integration.factories import TestClientFactory, TestUserFactory


@pytest.mark.django_db(transaction=True)
def test_with_mocked_service(
        container: AutoRegisteringContainer,
        user_factory: TestUserFactory,
) -> None:
    # Step 1: Create mock with spec (type safety)
    mock_service = MagicMock(spec=ProductService)

    # Step 2: Configure mock behavior
    mock_service.get_by_id.return_value = MagicMock(
        id=1,
        name="Mocked Product",
        price=99.99,
    )

    # Step 3: Override IoC registration BEFORE creating client
    container.register(ProductService, instance=mock_service)

    # Step 4: Create user and test client
    user = user_factory()
    test_client_factory = TestClientFactory(container=container)
    with test_client_factory(auth_for_user=user) as test_client:
        # Step 5: Make request
        response = test_client.get("/v1/products/1")

    # Step 6: Assert response
    assert response.status_code == 200
    assert response.json()["name"] == "Mocked Product"

    # Step 7: Verify mock was called correctly
    mock_service.get_by_id.assert_called_once_with(1)
```

## Mock Configuration Patterns

### Return Value

```python
# Simple value
mock_service.get_count.return_value = 42

# Object with attributes
mock_service.get_user.return_value = MagicMock(
    id=1,
    username="test",
    email="test@example.com",
)

# List of objects
mock_service.list_all.return_value = [
    MagicMock(id=1, name="Item 1"),
    MagicMock(id=2, name="Item 2"),
]
```

### Side Effects (Exceptions)

```python
# Raise exception
mock_service.get_by_id.side_effect = ProductNotFoundError("Not found")

# Raise different exceptions based on input
def side_effect(product_id: int):
    if product_id == 999:
        raise ProductNotFoundError(f"Product {product_id} not found")
    return MagicMock(id=product_id, name=f"Product {product_id}")

mock_service.get_by_id.side_effect = side_effect
```

### Multiple Return Values

```python
# Return different values on successive calls
mock_service.get_next.side_effect = [
    MagicMock(id=1),
    MagicMock(id=2),
    StopIteration,
]
```

### Conditional Returns

```python
def conditional_return(**kwargs):
    if kwargs.get("active"):
        return [MagicMock(id=1, active=True)]
    return []

mock_service.list_filtered.side_effect = conditional_return
```

## Mock Assertion Patterns

### Basic Assertions

```python
# Was called
mock_service.create.assert_called()

# Was called once
mock_service.create.assert_called_once()

# Was not called
mock_service.delete.assert_not_called()

# Call count
assert mock_service.get_by_id.call_count == 3
```

### Argument Assertions

```python
# Exact arguments
mock_service.create.assert_called_with(name="Test", price=99.99)

# Partial arguments (using ANY)
from unittest.mock import ANY
mock_service.create.assert_called_with(name="Test", price=ANY)

# Keyword arguments
mock_service.update.assert_called_with(
    product_id=1,
    name="Updated",
    description=ANY,
)
```

### Multiple Calls

```python
# Check all calls
assert mock_service.get_by_id.call_args_list == [
    call(1),
    call(2),
    call(3),
]

# Check specific call (0-indexed)
assert mock_service.get_by_id.call_args_list[0] == call(1)
```

## Service-Specific Mock Examples

### Mocking UserService

```python
@pytest.fixture
def mock_user_service() -> MagicMock:
    mock = MagicMock(spec=UserService)
    mock.get_by_id.return_value = MagicMock(
        id=1,
        username="test_user",
        email="test@example.com",
        is_active=True,
    )
    mock.create_user.return_value = MagicMock(
        id=2,
        username="new_user",
        email="new@example.com",
    )
    return mock
```

### Mocking JWTService

```python
@pytest.fixture
def mock_jwt_service() -> MagicMock:
    mock = MagicMock(spec=JWTService)
    mock.decode_token.return_value = {
        "sub": 1,
        "exp": 9999999999,
    }
    mock.issue_access_token.return_value = "mocked-access-token"
    mock.issue_refresh_token.return_value = "mocked-refresh-token"
    return mock


@pytest.mark.django_db(transaction=True)
def test_with_mocked_jwt(
    container: AutoRegisteringContainer,
    mock_jwt_service: MagicMock,
    test_client_factory: TestClientFactory,
    user_factory: TestUserFactory,
) -> None:
    container.register(JWTService, instance=mock_jwt_service)

    user = user_factory()
    with test_client_factory() as test_client:
        response = test_client.get(
            "/v1/users/me",
            headers={"Authorization": "Bearer any-token"},
        )

    mock_jwt_service.decode_token.assert_called_once_with(token="any-token")
```

### Mocking HealthService

```python
@pytest.fixture
def mock_health_service() -> MagicMock:
    mock = MagicMock(spec=HealthService)
    mock.check_system_health.return_value = None  # Success
    return mock


@pytest.fixture
def mock_unhealthy_service() -> MagicMock:
    mock = MagicMock(spec=HealthService)
    mock.check_system_health.side_effect = HealthCheckError("Database unreachable")
    return mock
```

## Testing Multiple Services

When you need to mock multiple services:

```python
@pytest.mark.django_db(transaction=True)
def test_with_multiple_mocks(
    container: AutoRegisteringContainer,
    user_factory: TestUserFactory,
) -> None:
    # Create all mocks
    mock_product_service = MagicMock(spec=ProductService)
    mock_inventory_service = MagicMock(spec=InventoryService)
    mock_notification_service = MagicMock(spec=NotificationService)

    # Configure behaviors
    mock_product_service.get_by_id.return_value = MagicMock(id=1, name="Product")
    mock_inventory_service.check_stock.return_value = 10
    mock_notification_service.send.return_value = True

    # Register all mocks BEFORE creating client
    container.register(ProductService, instance=mock_product_service)
    container.register(InventoryService, instance=mock_inventory_service)
    container.register(NotificationService, instance=mock_notification_service)

    # Now create client and test
    user = user_factory()
    test_client_factory = TestClientFactory(container=container)
    with test_client_factory(auth_for_user=user) as test_client:
        # Test endpoint that uses all three services
        response = test_client.post("/v1/orders/", json={"product_id": 1, "quantity": 5})

    assert response.status_code == 200
    mock_product_service.get_by_id.assert_called_once()
    mock_inventory_service.check_stock.assert_called_once()
    mock_notification_service.send.assert_called_once()
```

## Mocking External Dependencies

### Mocking HTTP Clients

```python
@pytest.fixture
def mock_http_client() -> MagicMock:
    mock = MagicMock()
    mock.get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"data": "mocked"},
    )
    return mock
```

### Mocking Database Results

```python
# When you need to mock QuerySet behavior
mock_queryset = MagicMock()
mock_queryset.__iter__.return_value = iter([
    MagicMock(id=1, name="Item 1"),
    MagicMock(id=2, name="Item 2"),
])
mock_queryset.count.return_value = 2

mock_service.list_all.return_value = mock_queryset
```

## Common Pitfalls

### Wrong Order

```python
# WRONG - Mock registered after client creation
user = user_factory()
with test_client_factory(auth_for_user=user) as test_client:
    container.register(Service, instance=mock_service)  # Too late!
    response = test_client.get("/v1/endpoint/")

# CORRECT - Mock registered before client creation
container.register(Service, instance=mock_service)
user = user_factory()
with test_client_factory(auth_for_user=user) as test_client:
    response = test_client.get("/v1/endpoint/")
```

### Missing spec Parameter

```python
# WRONG - No type safety
mock_service = MagicMock()
mock_service.non_existent_method()  # Won't fail!

# CORRECT - With spec for type safety
mock_service = MagicMock(spec=ProductService)
mock_service.non_existent_method()  # Will fail!
```

### Not Using Container from Fixture

```python
# WRONG - Creating new container
def test_something():
    container = ContainerFactory()()  # New container, not the test one!
    container.register(Service, instance=mock)

# CORRECT - Using fixture container
def test_something(container: AutoRegisteringContainer):  # Use fixture
    container.register(Service, instance=mock)
```
