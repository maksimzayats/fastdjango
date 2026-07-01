import logging
from dataclasses import dataclass
from typing import ClassVar

from diwire import Injected

from fastapi_template.core.health.exceptions.health_check import HealthCheckError
from fastapi_template.core.health.services.database_health_checker import (
    DatabaseHealthChecker,
)
from fastapi_template.foundation.use_case import BaseUseCase

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class SystemHealthUseCase(BaseUseCase):
    """Check required runtime dependencies for service readiness."""

    HEALTH_CHECK_ERROR: ClassVar = HealthCheckError  # noqa: WPS115
    UNEXPECTED_ERROR: ClassVar = Exception  # noqa: WPS115

    _database_health_checker: Injected[DatabaseHealthChecker]

    async def execute(self) -> None:
        """Probe database readiness and expose failures as health-check errors."""
        try:
            await self._database_health_checker.check_database()
        except self.UNEXPECTED_ERROR as e:
            logger.exception("Health check failed: database is not reachable")
            raise self.HEALTH_CHECK_ERROR from e
