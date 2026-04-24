import logging

from django.contrib.sessions.models import Session

from fastdjango.core.health.exceptions import HealthCheckError
from fastdjango.core.shared.use_cases import BaseUseCase

logger = logging.getLogger(__name__)


class SystemHealthUseCase(BaseUseCase):
    def check(self) -> None:
        """Check the health of the system components.

        Raises:
            HealthCheckError: If any component is not healthy.
        """
        try:
            # Perform a simple database query to check connectivity
            Session.objects.first()
        except Exception as e:
            logger.exception("Health check failed: database is not reachable")
            raise HealthCheckError from e
