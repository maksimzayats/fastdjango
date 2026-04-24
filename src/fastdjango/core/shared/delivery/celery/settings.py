from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
