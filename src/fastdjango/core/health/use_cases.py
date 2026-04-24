import logging

from django.contrib.sessions.models import Session

from fastdjango.core.health.exceptions import HealthCheckError

logger = logging.getLogger(__name__)


class SystemHealthUseCase:
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
