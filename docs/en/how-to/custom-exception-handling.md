# Custom Exception Handling

Map domain exceptions to appropriate HTTP responses.

## Goal

Convert service-level exceptions into meaningful HTTP error responses.

## Prerequisites

- A controller extending `Controller` or `TransactionController`
- Domain exceptions defined in your service

## The Pattern

Override `handle_exception()` in your controller:

```python
from typing import Any

from fastapi import HTTPException, status


def handle_exception(self, exception: Exception) -> Any:
    if isinstance(exception, YourDomainError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exception),
        ) from exception
    return super().handle_exception(exception)
```

## Step-by-Step

### 1. Define Domain Exceptions

Create exceptions in your service file:

```python
# src/core/order/services.py
from core.exceptions import ApplicationError


class OrderNotFoundError(ApplicationError):
    """Raised when an order cannot be found."""


class OrderAlreadyPaidError(ApplicationError):
    """Raised when trying to pay an already paid order."""


class InsufficientStockError(ApplicationError):
    """Raised when stock is insufficient for order."""


class InvalidOrderStateError(ApplicationError):
    """Raised when order operation is invalid for current state."""
```

### 2. Raise Exceptions in Service

```python
@dataclass(kw_only=True)
class OrderService:
    def get_order_by_id(self, order_id: int) -> Order:
        try:
            return Order.objects.get(id=order_id)
        except Order.DoesNotExist as e:
            raise OrderNotFoundError(f"Order {order_id} not found") from e

    def pay_order(self, order_id: int) -> Order:
        order = self.get_order_by_id(order_id)

        if order.status == OrderStatus.PAID:
            raise OrderAlreadyPaidError(f"Order {order_id} is already paid")

        if order.status != OrderStatus.PENDING:
            raise InvalidOrderStateError(
                f"Cannot pay order in {order.status} state"
            )

        order.status = OrderStatus.PAID
        order.save()
        return order
```

### 3. Map Exceptions in Controller

```python
# src/delivery/http/controllers/order/controllers.py
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException, status

from core.order.services import (
    InsufficientStockError,
    InvalidOrderStateError,
    OrderAlreadyPaidError,
    OrderNotFoundError,
    OrderService,
)
from infrastructure.delivery.controllers import TransactionController


@dataclass(kw_only=True)
class OrderController(TransactionController):
    _order_service: OrderService

    def register(self, registry: APIRouter) -> None:
        registry.add_api_route(
            path="/v1/orders/{order_id}/pay",
            endpoint=self.pay_order,
            methods=["POST"],
        )

    def pay_order(self, order_id: int) -> OrderSchema:
        order = self._order_service.pay_order(order_id)
        return OrderSchema.model_validate(order, from_attributes=True)

    def handle_exception(self, exception: Exception) -> Any:
        # 404 - Resource not found
        if isinstance(exception, OrderNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exception),
            ) from exception

        # 409 - Conflict (already in desired state)
        if isinstance(exception, OrderAlreadyPaidError):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exception),
            ) from exception

        # 422 - Unprocessable (invalid state for operation)
        if isinstance(exception, InvalidOrderStateError):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exception),
            ) from exception

        # 400 - Bad request (insufficient stock)
        if isinstance(exception, InsufficientStockError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exception),
            ) from exception

        # Re-raise unknown exceptions
        return super().handle_exception(exception)
```

## Exception to HTTP Status Mapping

| Exception Type | HTTP Status | When to Use |
|----------------|-------------|-------------|
| `NotFoundError` | 404 | Resource doesn't exist |
| `AccessDeniedError` | 403 | User can't access resource |
| `AlreadyExistsError` | 409 | Resource already exists |
| `InvalidStateError` | 422 | Operation invalid for current state |
| `ValidationError` | 400 | Input validation failed |
| `InsufficientError` | 400 | Not enough resources |
| `UnauthorizedError` | 401 | Authentication required/failed |

## Structured Error Responses

For more detailed error responses, create an error schema:

```python
# src/delivery/http/controllers/common/schemas.py
from pydantic import BaseModel


class ErrorResponseSchema(BaseModel):
    error: str
    code: str
    details: dict | None = None
```

Then use it in exception handling:

```python
def handle_exception(self, exception: Exception) -> Any:
    if isinstance(exception, InsufficientStockError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": str(exception),
                "code": "INSUFFICIENT_STOCK",
                "details": {
                    "requested": exception.requested,
                    "available": exception.available,
                },
            },
        ) from exception
```

## Multiple Exception Types

Handle multiple similar exceptions together:

```python
def handle_exception(self, exception: Exception) -> Any:
    # Group 404 errors
    not_found_errors = (
        OrderNotFoundError,
        ProductNotFoundError,
        UserNotFoundError,
    )
    if isinstance(exception, not_found_errors):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exception),
        ) from exception

    # Group permission errors
    permission_errors = (
        AccessDeniedError,
        InsufficientPermissionsError,
    )
    if isinstance(exception, permission_errors):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exception),
        ) from exception

    return super().handle_exception(exception)
```

## Testing Exception Handling

```python
@pytest.mark.django_db(transaction=True)
class TestOrderController:
    def test_pay_order_not_found(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        with test_client_factory(auth_for_user=user) as client:
            response = client.post("/v1/orders/99999/pay")

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_pay_order_already_paid(
        self,
        test_client_factory: TestClientFactory,
        user: User,
        paid_order: Order,
    ) -> None:
        with test_client_factory(auth_for_user=user) as client:
            response = client.post(f"/v1/orders/{paid_order.id}/pay")

        assert response.status_code == HTTPStatus.CONFLICT
```

## Best Practices

1. **Be specific**: Use descriptive exception classes, not generic `Exception`
2. **Include context**: Pass relevant IDs and values in exception messages
3. **Use appropriate status codes**: Follow HTTP semantics
4. **Chain exceptions**: Use `from exception` to preserve stack trace
5. **Call super()**: Always call `super().handle_exception()` for unknown exceptions
