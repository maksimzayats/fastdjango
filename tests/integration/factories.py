from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from typing import Any

from celery.contrib.testing import worker
from celery.worker import WorkController
from fastapi.testclient import TestClient

from core.user.models import User
from core.user.services.jwt import JWTService
from delivery.http.factories import FastAPIFactory
from delivery.tasks.factories import CeleryAppFactory, TasksRegistryFactory
from delivery.tasks.registry import TasksRegistry
from infrastructure.frameworks.punq.auto_registering import AutoRegisteringContainer


class BaseFactory(ABC):
    __test__ = False

    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        pass


class ContainerBasedFactory(BaseFactory, ABC):
    def __init__(
        self,
        container: AutoRegisteringContainer,
    ) -> None:
        self._container = container


class TestClientFactory(ContainerBasedFactory):
    def __call__(
        self,
        auth_for_user: User | None = None,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> TestClient:
        api_factory = self._container.resolve(FastAPIFactory)
        jwt_service = self._container.resolve(JWTService)

        headers = headers or {}

        if auth_for_user is not None:
            token = jwt_service.issue_access_token(user_id=auth_for_user.pk)
            headers["Authorization"] = f"Bearer {token}"

        app = api_factory(
            include_django=False,
            add_trusted_hosts_middleware=False,
            add_cors_middleware=False,
        )

        return TestClient(
            app=app,
            headers=headers,
            base_url="http://testserver",
            **kwargs,
        )


class TestUserFactory(ContainerBasedFactory):
    def __call__(
        self,
        username: str = "test_user",
        password: str = "password123",  # noqa: S107
        email: str = "user@test.com",
        *,
        is_staff: bool = False,
        **kwargs: Any,
    ) -> User:
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=is_staff,
            **kwargs,
        )


class TestCeleryWorkerFactory(ContainerBasedFactory):
    def __call__(self) -> AbstractContextManager[WorkController]:
        celery_app_factory = self._container.resolve(CeleryAppFactory)

        return worker.start_worker(
            app=celery_app_factory(),
            perform_ping_check=False,
        )


class TestTasksRegistryFactory(ContainerBasedFactory):
    def __call__(self) -> TasksRegistry:
        factory = self._container.resolve(TasksRegistryFactory)
        return factory()
