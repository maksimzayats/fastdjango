# Override IoC in Tests

Mock dependencies for isolated testing.

## Goal

Replace real services with mocks in tests to:

- Test components in isolation
- Control service behavior
- Avoid external dependencies

## Prerequisites

- Understanding of [IoC Container](../concepts/ioc-container.md)
- pytest fixtures set up

## The Pattern

Register a mock before creating test factories:

```python
from unittest.mock import MagicMock

def test_with_mock(container: AutoRegisteringContainer) -> None:
    # 1. Create mock
    mock_service = MagicMock()

    # 2. Register mock in container
    container.register(MyService, instance=mock_service)

    # 3. Create test client (uses container with mock)
    test_client_factory = TestClientFactory(container=container)

    # 4. Test - controller now uses mock
    with test_client_factory() as client:
        response = client.get("/v1/endpoint")
```

## Step-by-Step Examples

### Mock a Service

```python
from unittest.mock import MagicMock

import pytest

from core.payment.services import PaymentService
from tests.integration.factories import TestClientFactory


@pytest.mark.django_db(transaction=True)
def test_checkout_with_mock_payment(
    container: AutoRegisteringContainer,
) -> None:
    # Create mock payment service
    mock_payment = MagicMock(spec=PaymentService)
    mock_payment.process_payment.return_value = {"status": "success", "id": "pay_123"}

    # Register mock
    container.register(PaymentService, instance=mock_payment)

    # Create test client with mocked container
    test_client_factory = TestClientFactory(container=container)

    with test_client_factory() as client:
        response = client.post(
            "/v1/checkout",
            json={"cart_id": 1, "payment_method": "card"},
        )

    # Verify mock was called
    mock_payment.process_payment.assert_called_once()
    assert response.status_code == 200
```

### Mock a Service with Specific Return Values

```python
@pytest.mark.django_db(transaction=True)
def test_product_with_mock_inventory(
    container: AutoRegisteringContainer,
    user: User,
) -> None:
    # Mock inventory service
    mock_inventory = MagicMock(spec=InventoryService)
    mock_inventory.check_stock.return_value = 100
    mock_inventory.reserve_stock.return_value = True

    container.register(InventoryService, instance=mock_inventory)

    test_client_factory = TestClientFactory(container=container)

    with test_client_factory(auth_for_user=user) as client:
        response = client.post(
            "/v1/orders",
            json={"product_id": 1, "quantity": 5},
        )

    # Verify stock was checked and reserved
    mock_inventory.check_stock.assert_called_with(product_id=1)
    mock_inventory.reserve_stock.assert_called_with(product_id=1, quantity=5)
```

### Mock to Raise Exceptions

```python
from core.email.services import EmailService, EmailDeliveryError


@pytest.mark.django_db(transaction=True)
def test_handles_email_failure(
    container: AutoRegisteringContainer,
    user: User,
) -> None:
    # Mock email service to fail
    mock_email = MagicMock(spec=EmailService)
    mock_email.send_email.side_effect = EmailDeliveryError("SMTP connection failed")

    container.register(EmailService, instance=mock_email)

    test_client_factory = TestClientFactory(container=container)

    with test_client_factory(auth_for_user=user) as client:
        response = client.post(
            "/v1/users/me/password-reset",
            json={"email": "user@example.com"},
        )

    # Should handle gracefully, not expose internal error
    assert response.status_code == 500  # Or whatever your error handling returns
```

### Mock Settings

```python
from core.feature.settings import FeatureSettings


@pytest.mark.django_db(transaction=True)
def test_with_feature_flag_enabled(
    container: AutoRegisteringContainer,
) -> None:
    # Create mock settings
    mock_settings = MagicMock(spec=FeatureSettings)
    mock_settings.new_feature_enabled = True
    mock_settings.feature_limit = 100

    container.register(FeatureSettings, instance=mock_settings)

    test_client_factory = TestClientFactory(container=container)

    with test_client_factory() as client:
        response = client.get("/v1/feature")

    assert response.status_code == 200
    # Feature should be available
```

### Using pytest Fixtures for Common Mocks

```python
# tests/integration/conftest.py
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_external_api(container: AutoRegisteringContainer) -> MagicMock:
    """Fixture providing a mocked external API client."""
    mock = MagicMock(spec=ExternalAPIClient)
    mock.fetch_data.return_value = {"data": "mocked"}
    container.register(ExternalAPIClient, instance=mock)
    return mock


# Usage in tests
@pytest.mark.django_db(transaction=True)
def test_uses_external_api(
    test_client_factory: TestClientFactory,
    mock_external_api: MagicMock,
    user: User,
) -> None:
    mock_external_api.fetch_data.return_value = {"special": "value"}

    with test_client_factory(auth_for_user=user) as client:
        response = client.get("/v1/external-data")

    assert response.json()["data"]["special"] == "value"
```

## Testing with Real Services

Sometimes you want to test with real services but control the data:

```python
@pytest.mark.django_db(transaction=True)
def test_with_real_service(
    test_client_factory: TestClientFactory,
    user: User,
) -> None:
    # Create real test data
    Product.objects.create(name="Test", price=10.00, stock=50)

    # Test with real service (no mocking)
    with test_client_factory(auth_for_user=user) as client:
        response = client.get("/v1/products")

    assert response.status_code == 200
    assert len(response.json()) == 1
```

## Testing Celery Tasks

For Celery tasks, mock at the service level:

```python
@pytest.mark.django_db(transaction=True)
def test_task_with_mock(
    container: AutoRegisteringContainer,
    celery_worker_factory: TestCeleryWorkerFactory,
    tasks_registry_factory: TestTasksRegistryFactory,
) -> None:
    # Mock the service used by the task
    mock_service = MagicMock(spec=NotificationService)
    container.register(NotificationService, instance=mock_service)

    registry = tasks_registry_factory()

    with celery_worker_factory():
        registry.send_notification.delay(user_id=1).get(timeout=10)

    mock_service.send.assert_called_once()
```

## Best Practices

### Do: Use `spec` Parameter

```python
# Good - validates mock usage matches real interface
mock = MagicMock(spec=PaymentService)

# Bad - no validation, can call non-existent methods
mock = MagicMock()
```

### Do: Register Mocks Before Creating Factories

```python
# Correct order
container.register(Service, instance=mock)
test_client_factory = TestClientFactory(container=container)

# Wrong - factory already created with real service
test_client_factory = TestClientFactory(container=container)
container.register(Service, instance=mock)  # Too late!
```

### Do: Use Fixture Order

```python
# container fixture must come first
def test_something(
    container: AutoRegisteringContainer,  # First - creates container
    test_client_factory: TestClientFactory,  # Uses container
    user: User,  # Uses database
) -> None:
    ...
```

### Don't: Mutate Shared State

```python
# Bad - modifies shared mock affecting other tests
mock_service.some_attribute = "changed"

# Good - create fresh mock per test
mock_service = MagicMock(spec=Service)
```

## Summary

1. Create mocks with `MagicMock(spec=RealClass)`
2. Register mocks in container before creating factories
3. Use fixtures for commonly mocked services
4. Verify mock interactions with `assert_called_*` methods
