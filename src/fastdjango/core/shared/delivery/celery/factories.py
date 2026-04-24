from dataclasses import dataclass, field

from celery import Celery
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastdjango.core.health.delivery.celery.tasks import PingTaskController
from fastdjango.core.shared.delivery.celery.registry import TaskName, TasksRegistry
from fastdjango.infrastructure.shared import ApplicationSettings


class CeleryBrokerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    url: SecretStr


class CelerySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CELERY_")

    # Worker settings
    worker_prefetch_multiplier: int = 1  # Fair task distribution
    worker_max_tasks_per_child: int | None = 1000  # Prevent memory leaks
    worker_max_memory_per_child: int | None = None  # KB, optional memory limit

    # Task execution
    task_acks_late: bool = True  # Acknowledge after execution
    task_reject_on_worker_lost: bool = True  # Requeue if worker dies
    task_time_limit: int | None = 300  # Hard limit: 5 minutes
    task_soft_time_limit: int | None = 270  # Soft limit: 4.5 minutes

    # Result backend
    result_expires: int = 3600  # 1 hour (reduce from default 24h)
    result_backend_always_retry: bool = True  # Retry on transient errors
    result_backend_max_retries: int = 10

    # Connection resilience
    broker_connection_retry_on_startup: bool = True
    broker_connection_max_retries: int | None = 10

    # Serialization
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: list[str] = Field(default_factory=lambda: ["json"])

    # Monitoring
    worker_send_task_events: bool = True  # Enable for Flower monitoring
    task_send_sent_event: bool = True


@dataclass(kw_only=True)
class CeleryAppFactory:
    _application_settings: ApplicationSettings
    _celery_settings: CelerySettings
    _broker_settings: CeleryBrokerSettings
    _instance: Celery | None = field(default=None, init=False)

    def __call__(self) -> Celery:
        if self._instance is not None:
            return self._instance

        celery_app = Celery(
            "main",
            broker=self._broker_settings.url.get_secret_value(),
            backend=self._broker_settings.url.get_secret_value(),
        )

        self._configure_app(celery_app=celery_app)
        self._configure_beat_schedule(celery_app=celery_app)

        self._instance = celery_app
        return self._instance

    def _configure_app(self, celery_app: Celery) -> None:
        celery_app.conf.update(
            timezone=self._application_settings.time_zone,
            enable_utc=True,
            **self._celery_settings.model_dump(),
        )

    def _configure_beat_schedule(self, celery_app: Celery) -> None:
        celery_app.conf.beat_schedule = {
            "ping-every-minute": {
                "task": TaskName.PING,
                "schedule": 60.0,
            },
        }


@dataclass(kw_only=True)
class TasksRegistryFactory:
    _celery_app_factory: CeleryAppFactory
    _ping_controller: PingTaskController
    _instance: TasksRegistry | None = field(default=None, init=False)

    def __call__(self) -> TasksRegistry:
        if self._instance is not None:
            return self._instance

        celery_app = self._celery_app_factory()
        registry = TasksRegistry(_celery_app=celery_app)
        self._ping_controller.register(celery_app)

        self._instance = registry
        return self._instance
