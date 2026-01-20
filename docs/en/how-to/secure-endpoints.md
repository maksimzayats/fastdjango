# Secure Endpoints

Add authentication and permission checks to API endpoints.

## Goal

Protect endpoints with JWT authentication and role-based access control.

## Prerequisites

- Understanding of [Factory Pattern](../concepts/factory-pattern.md)
- A controller with endpoints to secure

## Authentication Levels

| Level | Factory Call | Requirement |
|-------|--------------|-------------|
| Public | None | No authentication |
| Authenticated | `_jwt_auth_factory()` | Valid JWT token |
| Staff | `_jwt_auth_factory(require_staff=True)` | `user.is_staff=True` |
| Superuser | `_jwt_auth_factory(require_superuser=True)` | `user.is_superuser=True` |

## Step-by-Step

### 1. Inject the Factory

```python
from dataclasses import dataclass

from delivery.http.auth.jwt import JWTAuthFactory


@dataclass(kw_only=True)
class ProductController(TransactionController):
    _product_service: ProductService
    _jwt_auth_factory: JWTAuthFactory

    # Auth dependencies are created in __post_init__
```

### 2. Create Auth Dependencies in `__post_init__`

```python
def __post_init__(self) -> None:
    self._jwt_auth = self._jwt_auth_factory()
    self._staff_auth = self._jwt_auth_factory(require_staff=True)
    self._superuser_auth = self._jwt_auth_factory(require_superuser=True)
    super().__post_init__()
```

### 3. Apply to Routes

```python
from fastapi import APIRouter, Depends


def register(self, registry: APIRouter) -> None:
    # Public endpoint - no auth
    registry.add_api_route(
        path="/v1/products",
        endpoint=self.list_products,
        methods=["GET"],
    )

    # Authenticated users only
    registry.add_api_route(
        path="/v1/products/favorites",
        endpoint=self.list_favorites,
        methods=["GET"],
        dependencies=[Depends(self._jwt_auth)],
    )

    # Staff only
    registry.add_api_route(
        path="/v1/products",
        endpoint=self.create_product,
        methods=["POST"],
        dependencies=[Depends(self._staff_auth)],
    )

    # Superuser only
    registry.add_api_route(
        path="/v1/products/{product_id}",
        endpoint=self.delete_product,
        methods=["DELETE"],
        dependencies=[Depends(self._superuser_auth)],
    )
```

### 4. Access the Authenticated User

Use `AuthenticatedRequest` to access the user:

```python
from delivery.http.auth.jwt import AuthenticatedRequest


def list_favorites(self, request: AuthenticatedRequest) -> list[ProductSchema]:
    user = request.state.user
    return self._product_service.list_favorites_for_user(user)
```

## Complete Example

```python
# src/delivery/http/controllers/product/controllers.py
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from core.product.services import ProductNotFoundError, ProductService
from delivery.http.auth.jwt import (
    AuthenticatedRequest,
    JWTAuthFactory,
)
from delivery.http.controllers.product.schemas import (
    CreateProductRequestSchema,
    ProductSchema,
)
from infrastructure.delivery.controllers import TransactionController


@dataclass(kw_only=True)
class ProductController(TransactionController):
    _product_service: ProductService
    _jwt_auth_factory: JWTAuthFactory

    def __post_init__(self) -> None:
        self._jwt_auth = self._jwt_auth_factory()
        self._staff_auth = self._jwt_auth_factory(require_staff=True)
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        # Public - anyone can view products
        registry.add_api_route(
            path="/v1/products",
            endpoint=self.list_products,
            methods=["GET"],
            response_model=list[ProductSchema],
        )

        # Authenticated - users can view their favorites
        registry.add_api_route(
            path="/v1/products/favorites",
            endpoint=self.list_favorites,
            methods=["GET"],
            response_model=list[ProductSchema],
            dependencies=[Depends(self._jwt_auth)],
        )

        # Staff - only staff can create products
        registry.add_api_route(
            path="/v1/products",
            endpoint=self.create_product,
            methods=["POST"],
            response_model=ProductSchema,
            status_code=status.HTTP_201_CREATED,
            dependencies=[Depends(self._staff_auth)],
        )

    # Public endpoint - no request parameter needed
    def list_products(self) -> list[ProductSchema]:
        products = self._product_service.list_products()
        return [
            ProductSchema.model_validate(p, from_attributes=True)
            for p in products
        ]

    # Authenticated endpoint - uses AuthenticatedRequest
    def list_favorites(
        self,
        request: AuthenticatedRequest,
    ) -> list[ProductSchema]:
        user = request.state.user
        products = self._product_service.list_favorites(user)
        return [
            ProductSchema.model_validate(p, from_attributes=True)
            for p in products
        ]

    # Staff endpoint - uses AuthenticatedRequest
    def create_product(
        self,
        request: AuthenticatedRequest,
        body: CreateProductRequestSchema,
    ) -> ProductSchema:
        # request.state.user is guaranteed to be staff
        product = self._product_service.create_product(
            name=body.name,
            price=body.price,
        )
        return ProductSchema.model_validate(product, from_attributes=True)
```

## HTTP Response Codes

| Situation | Status Code |
|-----------|-------------|
| No token provided | 403 Forbidden |
| Invalid/expired token | 401 Unauthorized |
| Valid token, not staff | 403 Forbidden |
| Valid token, not superuser | 403 Forbidden |

## Rate Limiting

For additional security, add rate limiting:

```python
from delivery.http.services.throttler import IPThrottler, UserThrottler
from throttled import rate_limiter


@dataclass(kw_only=True)
class AuthController(TransactionController):
    _ip_throttler: IPThrottler

    def register(self, registry: APIRouter) -> None:
        registry.add_api_route(
            path="/v1/auth/login",
            endpoint=self.login,
            methods=["POST"],
        )

    def login(self, request: Request, body: LoginSchema) -> TokenSchema:
        # Rate limit by IP: 10 attempts per minute
        self._ip_throttler.check(request, rate_limiter.per_min(10))

        # ... login logic ...
```

## Testing Secured Endpoints

```python
@pytest.mark.django_db(transaction=True)
class TestProductController:
    def test_public_endpoint(
        self,
        test_client_factory: TestClientFactory,
    ) -> None:
        # No auth needed
        with test_client_factory() as client:
            response = client.get("/v1/products")

        assert response.status_code == HTTPStatus.OK

    def test_authenticated_endpoint(
        self,
        test_client_factory: TestClientFactory,
        user: User,
    ) -> None:
        # auth_for_user auto-generates token
        with test_client_factory(auth_for_user=user) as client:
            response = client.get("/v1/products/favorites")

        assert response.status_code == HTTPStatus.OK

    def test_staff_endpoint_as_regular_user(
        self,
        test_client_factory: TestClientFactory,
        user: User,  # Regular user, not staff
    ) -> None:
        with test_client_factory(auth_for_user=user) as client:
            response = client.post(
                "/v1/products",
                json={"name": "Test", "price": "9.99"},
            )

        assert response.status_code == HTTPStatus.FORBIDDEN

    def test_staff_endpoint_as_staff(
        self,
        test_client_factory: TestClientFactory,
        user_factory: TestUserFactory,
    ) -> None:
        staff_user = user_factory(is_staff=True)

        with test_client_factory(auth_for_user=staff_user) as client:
            response = client.post(
                "/v1/products",
                json={"name": "Test", "price": "9.99"},
            )

        assert response.status_code == HTTPStatus.CREATED
```

## Best Practices

1. **Default to authenticated**: Require auth unless explicitly public
2. **Use appropriate level**: Don't over-restrict (staff vs superuser)
3. **Check ownership**: Even authenticated users should only access their own data
4. **Rate limit sensitive endpoints**: Protect login, password reset, etc.
5. **Log security events**: Track failed auth attempts
