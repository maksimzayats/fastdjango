import logging
from dataclasses import dataclass
from typing import ClassVar

from django.contrib.sessions.models import Session

from fastdjango.core.health.exceptions import HealthCheckError
from fastdjango.foundation.use_cases import BaseUseCase

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class SystemHealthUseCase(BaseUseCase):
    HEALTH_CHECK_ERROR: ClassVar = HealthCheckError
    UNEXPECTED_ERROR: ClassVar = Exception

    def check(self) -> None:
        """Check the health of the system components.

        Raises:
            HealthCheckError: If any component is not healthy.
        """
        try:
            # Perform a simple database query to check connectivity
            Session.objects.first()
        except self.UNEXPECTED_ERROR as e:
            logger.exception("Health check failed: database is not reachable")
            raise self.HEALTH_CHECK_ERROR from e
