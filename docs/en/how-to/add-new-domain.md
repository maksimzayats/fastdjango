# Add a New Domain

Create a complete feature domain with model, service, and HTTP API.

## Goal

Add a new domain (e.g., `product`, `order`, `comment`) with all required components.

## Prerequisites

- Development environment set up
- Understanding of [Service Layer](../concepts/service-layer.md)

## Checklist

- [ ] Create Django app in `core/<domain>/`
- [ ] Add to `installed_apps` in settings
- [ ] Create model in `models.py`
- [ ] Create service in `services.py`
- [ ] Create controller directory in `delivery/http/controllers/<domain>/`
- [ ] Create schemas in `schemas.py`
- [ ] Create controller in `controllers.py`
- [ ] Register controller in factory
- [ ] Create admin in `admin.py`
- [ ] Run migrations
- [ ] Write tests

## Step-by-Step

### 1. Create the Domain Directory

```bash
mkdir -p src/core/product
touch src/core/product/__init__.py
```

### 2. Register with Django

Edit `src/configs/django.py`:

```python
class DjangoSettings(BaseSettings):
    installed_apps: tuple[str, ...] = (
        # ... existing apps ...
        "core.product",  # Add new domain
    )
```

### 3. Create the Model

Create `src/core/product/models.py`:

```python
# src/core/product/models.py
from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name
```

### 4. Create the Service

Create `src/core/product/services.py`:

```python
# src/core/product/services.py
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from core.exceptions import ApplicationError
from core.product.models import Product


class ProductNotFoundError(ApplicationError):
    """Raised when a product cannot be found."""


@dataclass(kw_only=True)
class ProductService:
    def get_product_by_id(self, product_id: int) -> Product:
        try:
            return Product.objects.get(id=product_id)
        except Product.DoesNotExist as e:
            raise ProductNotFoundError(f"Product {product_id} not found") from e

    def list_products(self, *, active_only: bool = True) -> list[Product]:
        queryset = Product.objects.all()
        if active_only:
            queryset = queryset.filter(is_active=True)
        return list(queryset)

    @transaction.atomic
    def create_product(
        self,
        *,
        name: str,
        description: str = "",
        price: Decimal,
    ) -> Product:
        return Product.objects.create(
            name=name,
            description=description,
            price=price,
        )
```

### 5. Create the Controller Directory

```bash
mkdir -p src/delivery/http/controllers/product
touch src/delivery/http/controllers/product/__init__.py
```

### 6. Create Schemas

Create `src/delivery/http/controllers/product/schemas.py`:

```python
# src/delivery/http/controllers/product/schemas.py
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CreateProductRequestSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    price: Decimal = Field(..., gt=0, decimal_places=2)


class ProductSchema(BaseModel):
    id: int
    name: str
    description: str
    price: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 7. Create the Controller

Create `src/delivery/http/controllers/product/controllers.py`:

```python
# src/delivery/http/controllers/product/controllers.py
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from core.product.services import ProductNotFoundError, ProductService
from delivery.http.auth.jwt import JWTAuthFactory
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
        self._staff_auth = self._jwt_auth_factory(require_staff=True)
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        registry.add_api_route(
            path="/v1/products",
            endpoint=self.list_products,
            methods=["GET"],
            response_model=list[ProductSchema],
        )
        registry.add_api_route(
            path="/v1/products/{product_id}",
            endpoint=self.get_product,
            methods=["GET"],
            response_model=ProductSchema,
        )
        registry.add_api_route(
            path="/v1/products",
            endpoint=self.create_product,
            methods=["POST"],
            response_model=ProductSchema,
            status_code=status.HTTP_201_CREATED,
            dependencies=[Depends(self._staff_auth)],  # Staff only
        )

    def list_products(self) -> list[ProductSchema]:
        products = self._product_service.list_products()
        return [
            ProductSchema.model_validate(p, from_attributes=True)
            for p in products
        ]

    def get_product(self, product_id: int) -> ProductSchema:
        product = self._product_service.get_product_by_id(product_id)
        return ProductSchema.model_validate(product, from_attributes=True)

    def create_product(self, body: CreateProductRequestSchema) -> ProductSchema:
        product = self._product_service.create_product(
            name=body.name,
            description=body.description,
            price=body.price,
        )
        return ProductSchema.model_validate(product, from_attributes=True)

    def handle_exception(self, exception: Exception) -> Any:
        if isinstance(exception, ProductNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exception),
            ) from exception
        return super().handle_exception(exception)
```

### 8. Register the Controller

Edit `src/delivery/http/factories.py`:

```python
# Add import at the top
from delivery.http.controllers.product.controllers import ProductController


@dataclass(kw_only=True)
class FastAPIFactory:
    # ... existing controller fields ...
    _product_controller: ProductController  # Add this field

    def _register_controllers(self, app: FastAPI) -> None:
        # ... existing controller registrations ...

        # Register ProductController
        product_router = APIRouter(tags=["product"])
        self._product_controller.register(product_router)
        app.include_router(product_router)
```

The controller is declared as a dataclass field and auto-resolved by the IoC container.

### 9. Create Admin

Create `src/core/product/admin.py`:

```python
# src/core/product/admin.py
from django.contrib import admin

from core.product.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["-created_at"]
```

### 10. Run Migrations

```bash
make makemigrations
make migrate
```

### 11. Write Tests

Create `tests/integration/http/v1/test_v1_products.py`:

```python
# tests/integration/http/v1/test_v1_products.py
from decimal import Decimal
from http import HTTPStatus

import pytest

from core.product.models import Product
from core.user.models import User
from tests.integration.factories import TestClientFactory, TestUserFactory


@pytest.fixture
def staff_user(user_factory: TestUserFactory) -> User:
    return user_factory(username="staff", password="pass", is_staff=True)


@pytest.fixture
def product() -> Product:
    return Product.objects.create(
        name="Test Product",
        price=Decimal("9.99"),
    )


@pytest.mark.django_db(transaction=True)
class TestProductController:
    def test_list_products(
        self,
        test_client_factory: TestClientFactory,
        product: Product,
    ) -> None:
        with test_client_factory() as client:
            response = client.get("/v1/products")

        assert response.status_code == HTTPStatus.OK
        assert len(response.json()) == 1

    def test_create_product_staff_only(
        self,
        test_client_factory: TestClientFactory,
        staff_user: User,
    ) -> None:
        with test_client_factory(auth_for_user=staff_user) as client:
            response = client.post(
                "/v1/products",
                json={"name": "New Product", "price": "19.99"},
            )

        assert response.status_code == HTTPStatus.CREATED
```

## File Summary

| Action | File |
|--------|------|
| Create | `src/core/product/__init__.py` |
| Create | `src/core/product/models.py` |
| Create | `src/core/product/services.py` |
| Create | `src/core/product/admin.py` |
| Create | `src/delivery/http/controllers/product/__init__.py` |
| Create | `src/delivery/http/controllers/product/schemas.py` |
| Create | `src/delivery/http/controllers/product/controllers.py` |
| Modify | `src/configs/django.py` |
| Modify | `src/delivery/http/factories.py` |
| Create | `tests/integration/http/v1/test_v1_products.py` |

## Verification

1. Start the server: `make dev`
2. Check the API docs: http://localhost:8000/docs
3. Verify the new endpoints appear
4. Run tests: `make test`
