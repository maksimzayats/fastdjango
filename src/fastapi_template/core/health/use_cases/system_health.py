import logging
from dataclasses import dataclass
from typing import ClassVar

from diwire import Injected

from fastapi_template.core.health.exceptions.health_check import HealthCheckError
from fastapi_template.core.unit_of_work import UnitOfWork
from fastapi_template.foundation.use_case import BaseUseCase

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class SystemHealthUseCase(BaseUseCase):
    """Define SystemHealthUseCase."""

    HEALTH_CHECK_ERROR: ClassVar = HealthCheckError
    UNEXPECTED_ERROR: ClassVar = Exception

    _uow: Injected[UnitOfWork]

    async def execute(self) -> None:
        """Run execute."""
        try:
            async with self._uow as uow:
                await uow.health_repository.check_database()
        except self.UNEXPECTED_ERROR as e:
            logger.exception("Health check failed: database is not reachable")
            raise self.HEALTH_CHECK_ERROR from e
