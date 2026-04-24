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
- [ ] Create delivery directories in `core/<domain>/delivery/`
- [ ] Create schemas in `schemas.py`
- [ ] Create controller in `controllers.py`
- [ ] Register controller in factory
- [ ] Create admin in `delivery/django/admin.py`
- [ ] Run migrations
- [ ] Write tests

## Step-by-Step

### 1. Create the Domain Directory

```bash
mkdir -p src/fastdjango/core/product
touch src/fastdjango/core/product/__init__.py
```

Create `src/fastdjango/core/product/apps.py`:

```python
from django.apps import AppConfig


class ProductConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fastdjango.core.product"
    label = "product"
```

### 2. Register with Django

Edit `src/fastdjango/infrastructure/django/settings.py`:

```python
class DjangoSettings(BaseSettings):
    installed_apps: tuple[str, ...] = (
        # ... existing apps ...
        "fastdjango.core.product.apps.ProductConfig",  # Add new domain
    )
```

### 3. Create the Model

Create `src/fastdjango/core/product/models.py`:

```python
# src/fastdjango/core/product/models.py
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

Create `src/fastdjango/core/product/services.py`:

```python
# src/fastdjango/core/product/services.py
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from fastdjango.core.exceptions import ApplicationError
from fastdjango.core.shared.services import BaseService
from fastdjango.core.product.models import Product


class ProductNotFoundError(ApplicationError):
    """Raised when a product cannot be found."""


@dataclass(kw_only=True)
class ProductService(BaseService):
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

### 5. Create Delivery Directories

```bash
mkdir -p src/fastdjango/core/product/delivery/fastapi
touch src/fastdjango/core/product/delivery/fastapi/__init__.py
mkdir -p src/fastdjango/core/product/delivery/django
touch src/fastdjango/core/product/delivery/django/__init__.py
```

### 6. Create Schemas

Create `src/fastdjango/core/product/delivery/fastapi/schemas.py`:

```python
# src/fastdjango/core/product/delivery/fastapi/schemas.py
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from fastdjango.core.shared.delivery.fastapi.schemas import BaseFastAPISchema


class CreateProductRequestSchema(BaseFastAPISchema):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    price: Decimal = Field(..., gt=0, decimal_places=2)


class ProductSchema(BaseFastAPISchema):
    id: int
    name: str
    description: str
    price: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 7. Create the Controller

Create `src/fastdjango/core/product/delivery/fastapi/controllers.py`:

```python
# src/fastdjango/core/product/delivery/fastapi/controllers.py
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from fastdjango.core.product.services import ProductNotFoundError, ProductService
from fastdjango.core.authentication.delivery.fastapi.auth import JWTAuthFactory
from fastdjango.core.product.delivery.fastapi.schemas import (
    CreateProductRequestSchema,
    ProductSchema,
)
from fastdjango.infrastructure.delivery.controllers import TransactionController


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

Edit `src/fastdjango/core/shared/delivery/fastapi/factories.py`:

```python
# Add import at the top
from fastdjango.core.product.delivery.fastapi.controllers import ProductController


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

Create `src/fastdjango/core/product/delivery/django/admin.py`:

```python
# src/fastdjango/core/product/delivery/django/admin.py
from django.contrib import admin

from fastdjango.core.product.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "price", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["-created_at"]
```

Import the admin module from the domain app config so Django registers it:

```python
def ready(self) -> None:
    from fastdjango.core.product.delivery.django import admin as _product_admin  # noqa: F401, I001, PLC0415
```

### 10. Run Migrations

```bash
make makemigrations
make migrate
```

### 11. Write Tests

Create `tests/integration/fastapi/test_v1_products.py`:

```python
# tests/integration/fastapi/test_v1_products.py
from decimal import Decimal
from http import HTTPStatus

import pytest

from fastdjango.core.product.models import Product
from fastdjango.core.user.models import User
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
| Create | `src/fastdjango/core/product/__init__.py` |
| Create | `src/fastdjango/core/product/apps.py` |
| Create | `src/fastdjango/core/product/models.py` |
| Create | `src/fastdjango/core/product/services.py` |
| Create | `src/fastdjango/core/product/delivery/django/__init__.py` |
| Create | `src/fastdjango/core/product/delivery/django/admin.py` |
| Create | `src/fastdjango/core/product/delivery/fastapi/__init__.py` |
| Create | `src/fastdjango/core/product/delivery/fastapi/schemas.py` |
| Create | `src/fastdjango/core/product/delivery/fastapi/controllers.py` |
| Modify | `src/fastdjango/infrastructure/django/settings.py` |
| Modify | `src/fastdjango/core/product/apps.py` |
| Modify | `src/fastdjango/core/shared/delivery/fastapi/factories.py` |
| Create | `tests/integration/fastapi/test_v1_products.py` |

## Verification

1. Start the server: `make dev`
2. Check the API docs: http://localhost:8000/docs
3. Verify the new endpoints appear
4. Run tests: `make test`
