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
- [ ] Create model in `models.py` with explicit field verbose names
- [ ] Create domain exceptions in `exceptions.py`
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
mkdir -p src/modern_python_template/core/product
touch src/modern_python_template/core/product/__init__.py
```

Create `src/modern_python_template/core/product/apps.py`:

```python
from django.apps import AppConfig


class ProductConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modern_python_template.core.product"
    label = "product"
```

### 2. Register with Django

Edit `src/modern_python_template/infrastructure/django/settings.py`:

```python
class DjangoSettings(BaseSettings):
    installed_apps: tuple[str, ...] = (
        # ... existing apps ...
        "modern_python_template.core.product.apps.ProductConfig",  # Add new domain
    )
```

### 3. Create the Model

Create `src/modern_python_template/core/product/models.py`:

```python
# src/modern_python_template/core/product/models.py
from django.db import models


class Product(models.Model):
    name = models.CharField(verbose_name="name", max_length=200)
    description = models.TextField(verbose_name="description", blank=True)
    price = models.DecimalField(verbose_name="price", max_digits=10, decimal_places=2)
    is_active = models.BooleanField(verbose_name="is active", default=True)
    created_at = models.DateTimeField(verbose_name="created at", auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="updated at", auto_now=True)

    class Meta:
        verbose_name = "product"
        verbose_name_plural = "products"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name
```

### 4. Create Domain Exceptions

Create `src/modern_python_template/core/product/exceptions.py`:

```python
# src/modern_python_template/core/product/exceptions.py
from modern_python_template.core.exceptions import ApplicationError


class ProductNotFoundError(ApplicationError):
    """Raised when a product cannot be found."""
```

### 5. Create the Service

Create `src/modern_python_template/core/product/services.py`:

```python
# src/modern_python_template/core/product/services.py
from dataclasses import dataclass
from decimal import Decimal

from asgiref.sync import sync_to_async
from diwire import Injected

from modern_python_template.core.product.exceptions import ProductNotFoundError
from modern_python_template.foundation.services import BaseService
from modern_python_template.foundation.transactions import TransactionFactory
from modern_python_template.core.product.models import Product


@dataclass(kw_only=True)
class ProductService(BaseService):
    _transaction_factory: Injected[TransactionFactory]

    async def get_product_by_id(self, *, product_id: int) -> Product:
        try:
            return await Product.objects.aget(id=product_id)
        except Product.DoesNotExist as e:
            raise ProductNotFoundError(f"Product {product_id} not found") from e

    async def list_products(self, *, active_only: bool = True) -> list[Product]:
        queryset = Product.objects.all()
        if active_only:
            queryset = queryset.filter(is_active=True)
        return [product async for product in queryset]

    async def create_product(
        self,
        *,
        name: str,
        description: str = "",
        price: Decimal,
    ) -> Product:
        return await sync_to_async(
            self._create_product_transactionally,
            thread_sensitive=True,
        )(name=name, description=description, price=price)

    def _create_product_transactionally(
        self,
        *,
        name: str,
        description: str = "",
        price: Decimal,
    ) -> Product:
        with self._transaction_factory(span_name="create product"):
            return Product.objects.create(
                name=name,
                description=description,
                price=price,
            )
```

### 6. Create Delivery Directories

```bash
mkdir -p src/modern_python_template/core/product/delivery/fastapi
touch src/modern_python_template/core/product/delivery/fastapi/__init__.py
mkdir -p src/modern_python_template/core/product/delivery/django
touch src/modern_python_template/core/product/delivery/django/__init__.py
```

### 7. Create Schemas

Create `src/modern_python_template/core/product/delivery/fastapi/schemas.py`:

```python
# src/modern_python_template/core/product/delivery/fastapi/schemas.py
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from modern_python_template.foundation.delivery.fastapi.schemas import BaseFastAPISchema


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

### 8. Create the Controller

Create `src/modern_python_template/core/product/delivery/fastapi/controllers.py`:

```python
# src/modern_python_template/core/product/delivery/fastapi/controllers.py
from dataclasses import dataclass
from typing import Any

from diwire import Injected
from fastapi import APIRouter, Depends, HTTPException, status

from modern_python_template.core.product.exceptions import ProductNotFoundError
from modern_python_template.core.product.services import ProductService
from modern_python_template.core.authentication.delivery.fastapi.auth import JWTAuthFactory
from modern_python_template.core.product.delivery.fastapi.schemas import (
    CreateProductRequestSchema,
    ProductSchema,
)
from modern_python_template.foundation.delivery.controllers import BaseAsyncController


@dataclass(kw_only=True)
class ProductController(BaseAsyncController):
    _product_service: Injected[ProductService]
    _jwt_auth_factory: Injected[JWTAuthFactory]

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

    async def list_products(self) -> list[ProductSchema]:
        products = await self._product_service.list_products()
        return [
            ProductSchema.model_validate(p, from_attributes=True)
            for p in products
        ]

    async def get_product(self, product_id: int) -> ProductSchema:
        product = await self._product_service.get_product_by_id(product_id=product_id)
        return ProductSchema.model_validate(product, from_attributes=True)

    async def create_product(self, body: CreateProductRequestSchema) -> ProductSchema:
        product = await self._product_service.create_product(
            name=body.name,
            description=body.description,
            price=body.price,
        )
        return ProductSchema.model_validate(product, from_attributes=True)

    async def handle_exception(self, exception: Exception) -> Any:
        if isinstance(exception, ProductNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exception),
            ) from exception
        return await super().handle_exception(exception)
```

### 9. Register the Controller

Edit `src/modern_python_template/entrypoints/fastapi/factories.py`:

```python
# Add import at the top
from modern_python_template.core.product.delivery.fastapi.controllers import ProductController


@dataclass(kw_only=True)
class FastAPIFactory(BaseFactory):
    # ... existing controller fields ...
    _product_controller: Injected[ProductController]  # Add this field

    def _register_controllers(self, app: FastAPI) -> None:
        # ... existing controller registrations ...

        # Register ProductController
        product_router = APIRouter(tags=["product"])
        self._product_controller.register(product_router)
        app.include_router(product_router)
```

The controller is declared as a dataclass field and auto-resolved by the IoC container.

### 10. Create Admin

Create `src/modern_python_template/core/product/delivery/django/admin.py`:

```python
# src/modern_python_template/core/product/delivery/django/admin.py
from django.contrib import admin

from modern_python_template.core.product.models import Product


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
    from modern_python_template.core.product.delivery.django import admin as _product_admin  # noqa: F401, PLC0415
```

### 11. Run Migrations

```bash
make makemigrations
make migrate
```

### 12. Write Tests

Create `tests/integration/core/product/delivery/fastapi/test_controllers.py`:

```python
# tests/integration/core/product/delivery/fastapi/test_controllers.py
from decimal import Decimal
from http import HTTPStatus

import pytest

from modern_python_template.core.product.models import Product
from modern_python_template.core.user.models import User
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
| Create | `src/modern_python_template/core/product/__init__.py` |
| Create | `src/modern_python_template/core/product/apps.py` |
| Create | `src/modern_python_template/core/product/models.py` |
| Create | `src/modern_python_template/core/product/exceptions.py` |
| Create | `src/modern_python_template/core/product/services.py` |
| Create | `src/modern_python_template/core/product/delivery/django/__init__.py` |
| Create | `src/modern_python_template/core/product/delivery/django/admin.py` |
| Create | `src/modern_python_template/core/product/delivery/fastapi/__init__.py` |
| Create | `src/modern_python_template/core/product/delivery/fastapi/schemas.py` |
| Create | `src/modern_python_template/core/product/delivery/fastapi/controllers.py` |
| Modify | `src/modern_python_template/infrastructure/django/settings.py` |
| Modify | `src/modern_python_template/core/product/apps.py` |
| Modify | `src/modern_python_template/entrypoints/fastapi/factories.py` |
| Create | `tests/integration/core/product/delivery/fastapi/test_controllers.py` |

## Verification

1. Start the server: `make dev`
2. Check the API docs: http://localhost:8000/docs
3. Verify the new endpoints appear
4. Run tests: `make test`
