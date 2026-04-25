# Controller Patterns

## FastAPI Controller

```python
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from fastdjango.core.product.delivery.fastapi.schemas import ProductSchema
from fastdjango.core.product.exceptions import ProductNotFoundError
from fastdjango.core.product.use_cases import ProductUseCase
from fastdjango.core.authentication.delivery.fastapi.auth import JWTAuthFactory
from fastdjango.infrastructure.django.controllers import BaseTransactionController


@dataclass(kw_only=True)
class ProductController(BaseTransactionController):
    _jwt_auth_factory: JWTAuthFactory
    _product_use_case: ProductUseCase

    def __post_init__(self) -> None:
        self._jwt_auth = self._jwt_auth_factory()
        super().__post_init__()

    def register(self, registry: APIRouter) -> None:
        registry.add_api_route(
            path="/v1/products/{product_id}",
            endpoint=self.get_product,
            methods=["GET"],
            response_model=ProductSchema,
            dependencies=[Depends(self._jwt_auth)],
        )

    def get_product(self, product_id: int) -> ProductSchema:
        product = self._product_use_case.get_product_by_id(product_id)
        return ProductSchema.model_validate(product, from_attributes=True)

    def handle_exception(self, exception: Exception) -> Any:
        if isinstance(exception, ProductNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exception),
            ) from exception
        return super().handle_exception(exception)
```

Use `BaseTransactionController` for sync routes that touch Django ORM. Use
`BaseAsyncController` only for genuinely async routes, and keep Django ORM work
inside sync services or `sync_to_async`.

## Celery Task Controller

```python
from dataclasses import dataclass

from celery import Celery

from fastdjango.core.product.delivery.celery.schemas import CleanupResultSchema
from fastdjango.core.product.services import ProductCleanupService
from fastdjango.foundation.delivery.controllers import BaseController

PRODUCT_CLEANUP_TASK_NAME = "product.cleanup"


@dataclass(kw_only=True)
class ProductCleanupTaskController(BaseController):
    _cleanup_service: ProductCleanupService

    def register(self, registry: Celery) -> None:
        registry.task(name=PRODUCT_CLEANUP_TASK_NAME)(self.cleanup)

    def cleanup(self) -> CleanupResultSchema:
        deleted_count = self._cleanup_service.cleanup()
        return CleanupResultSchema(deleted_count=deleted_count)
```

Keep task-name constants in the domain task module. The entrypoint registry may
import those constants, but domain delivery should not import `TaskName` from the
entrypoint.
