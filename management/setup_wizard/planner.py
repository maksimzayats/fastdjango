from __future__ import annotations

import re
import textwrap
import tomllib
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from management.setup_wizard.config import (
    update_docker_compose_yaml,
    update_mkdocs_yaml,
    update_prek_toml,
    update_pyproject_toml,
    update_ruff_toml,
)
from management.setup_wizard.env import (
    build_env_content,
    build_env_example_content,
    build_test_env_example_content,
)
from management.setup_wizard.file_operations import FilePlan
from management.setup_wizard.models import AuthenticationMode, SetupAnswers
from management.setup_wizard.python_rewrite import rewrite_python_imports
from management.setup_wizard.readme import build_project_readme
from management.setup_wizard.text_rewrite import (
    ProjectReferences,
    replace_project_references,
)

DEFAULT_PACKAGE_NAME = "fastdjango"
EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "htmlcov",
    "site",
}


def build_setup_plan(
    *,
    repo_root: Path,
    answers: SetupAnswers,
    current_package_name: str | None = None,
) -> FilePlan:
    resolved_package_name = current_package_name or detect_current_package_name(repo_root=repo_root)
    plan = FilePlan(repo_root=repo_root)

    _plan_package_rename(
        plan=plan,
        answers=answers,
        current_package_name=resolved_package_name,
    )
    _plan_python_rewrites(
        plan=plan,
        answers=answers,
        current_package_name=resolved_package_name,
    )
    _plan_authentication_mode(
        plan=plan,
        answers=answers,
        current_package_name=resolved_package_name,
    )
    _plan_config_rewrites(
        plan=plan,
        answers=answers,
        current_package_name=resolved_package_name,
    )
    _plan_environment_files(plan=plan, answers=answers)
    _plan_docs(plan=plan, answers=answers, current_package_name=resolved_package_name)
    _plan_self_delete(plan=plan, answers=answers)
    plan.add_command(("uv", "lock"), detail="Refresh uv.lock")
    return plan


def detect_current_package_name(*, repo_root: Path) -> str:
    pyproject_path = repo_root / "pyproject.toml"
    if pyproject_path.exists():
        package_name = _detect_package_name_from_pyproject(pyproject_path=pyproject_path)
        if package_name is not None:
            return package_name

    src_path = repo_root / "src"
    if not src_path.exists():
        return DEFAULT_PACKAGE_NAME

    package_dirs = sorted(path.name for path in src_path.iterdir() if _is_python_package(path))
    if len(package_dirs) == 1:
        return package_dirs[0]

    return DEFAULT_PACKAGE_NAME


def _detect_package_name_from_pyproject(*, pyproject_path: Path) -> str | None:
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    django_settings_module = (
        pyproject.get("tool", {}).get("django-stubs", {}).get("django_settings_module")
    )
    if isinstance(django_settings_module, str) and "." in django_settings_module:
        return django_settings_module.split(".", maxsplit=1)[0]

    return None


def _plan_package_rename(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    source_path = plan.repo_root / "src" / current_package_name
    target_path = plan.repo_root / "src" / answers.package_name
    plan.add_rename(source_path, target_path, detail="Rename Python package")


def _plan_python_rewrites(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    for source_path in _iter_python_files(repo_root=plan.repo_root, answers=answers):
        content = source_path.read_text(encoding="utf-8")
        content = rewrite_python_imports(
            source=content,
            old_package_name=current_package_name,
            new_package_name=answers.package_name,
        )
        content = _replace_text_references(
            text=content,
            answers=answers,
            current_package_name=current_package_name,
        )
        plan.add_write(
            _target_path_for_package_rename(
                source_path=source_path,
                repo_root=plan.repo_root,
                current_package_name=current_package_name,
                new_package_name=answers.package_name,
            ),
            content=content,
            detail="Rewrite Python package references",
        )


def _plan_authentication_mode(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    if answers.authentication_mode == AuthenticationMode.JWT_REFRESH_SESSION:
        return

    _plan_remove_refresh_session_auth(
        plan=plan,
        answers=answers,
        current_package_name=current_package_name,
    )

    if answers.authentication_mode == AuthenticationMode.STATIC_API_KEYS:
        _plan_static_api_key_auth(plan=plan, answers=answers)
        return

    _plan_custom_auth(
        plan=plan,
        answers=answers,
        current_package_name=current_package_name,
    )


def _plan_remove_refresh_session_auth(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    package_path = _package_path(plan=plan, answers=answers)
    auth_path = package_path / "core" / "authentication"

    plan.add_write(
        package_path / "infrastructure" / "django" / "settings.py",
        content=_django_settings_without_authentication_app(
            plan=plan,
            answers=answers,
            current_package_name=current_package_name,
        ),
        detail="Remove refresh-session authentication Django app",
    )
    plan.add_write(
        package_path / "core" / "user" / "models.py",
        content=_user_model_without_refresh_sessions(),
        detail="Remove refresh-session reverse relation annotation",
    )

    source_auth_path = plan.repo_root / "src" / current_package_name / "core" / "authentication"
    for relative_path in (
        "apps.py",
        "dtos.py",
        "exceptions.py",
        "models.py",
        "use_cases.py",
        "delivery/django",
        "delivery/fastapi/controllers.py",
        "delivery/fastapi/schemas.py",
        "delivery/fastapi/throttling.py",
        "migrations",
        "services",
    ):
        plan.add_delete(
            auth_path / relative_path,
            detail="Remove refresh-session authentication code",
            exists_path=source_auth_path / relative_path,
        )

    for relative_path in (
        "tests/integration/core/authentication/delivery/fastapi/test_controllers.py",
        "tests/unit/core/authentication/services",
        "tests/unit/core/authentication/test_use_cases.py",
    ):
        plan.add_delete(
            plan.repo_root / relative_path,
            detail="Remove refresh-session authentication tests",
        )


def _plan_static_api_key_auth(*, plan: FilePlan, answers: SetupAnswers) -> None:
    package_name = answers.package_name
    package_path = _package_path(plan=plan, answers=answers)

    plan.add_write(
        package_path / "core" / "authentication" / "delivery" / "fastapi" / "auth.py",
        content=_static_api_key_auth_module(package_name=package_name),
        detail="Keep only static API key authentication",
    )
    plan.add_write(
        package_path / "entrypoints" / "fastapi" / "factories.py",
        content=_fastapi_factory_without_token_routes(package_name=package_name),
        detail="Remove refresh-session token routes",
    )
    plan.add_write(
        package_path / "core" / "user" / "delivery" / "fastapi" / "controllers.py",
        content=_static_api_key_user_controller(package_name=package_name),
        detail="Use static API key auth for protected user routes",
    )
    plan.add_write(
        plan.repo_root / "tests" / "integration" / "conftest.py",
        content=_static_api_key_integration_conftest(package_name=package_name),
        detail="Use static API keys in integration tests",
    )
    plan.add_write(
        plan.repo_root / "tests" / "integration" / "factories.py",
        content=_test_factories_without_jwt(package_name=package_name),
        detail="Remove JWT test client helper",
    )
    plan.add_write(
        plan.repo_root
        / "tests"
        / "integration"
        / "core"
        / "authentication"
        / "delivery"
        / "fastapi"
        / "test_auth.py",
        content=_static_api_key_integration_auth_test(package_name=package_name),
        detail="Test static API key authentication",
    )
    plan.add_write(
        plan.repo_root
        / "tests"
        / "unit"
        / "core"
        / "authentication"
        / "delivery"
        / "fastapi"
        / "test_auth.py",
        content=_static_api_key_unit_auth_test(package_name=package_name),
        detail="Test static API key auth dependency",
    )
    plan.add_write(
        plan.repo_root
        / "tests"
        / "integration"
        / "core"
        / "user"
        / "delivery"
        / "fastapi"
        / "test_controllers.py",
        content=_static_api_key_user_controller_test(package_name=package_name),
        detail="Use static API key auth in user controller tests",
    )


def _plan_custom_auth(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    package_name = answers.package_name
    package_path = _package_path(plan=plan, answers=answers)

    plan.add_delete(
        package_path / "core" / "authentication",
        detail="Remove built-in authentication code",
        exists_path=plan.repo_root / "src" / current_package_name / "core" / "authentication",
    )
    plan.add_delete(
        plan.repo_root / "tests" / "integration" / "core" / "authentication",
        detail="Remove built-in authentication tests",
    )
    plan.add_delete(
        plan.repo_root / "tests" / "unit" / "core" / "authentication",
        detail="Remove built-in authentication tests",
    )
    plan.add_write(
        package_path / "entrypoints" / "fastapi" / "factories.py",
        content=_fastapi_factory_without_token_routes(package_name=package_name),
        detail="Remove built-in authentication routes",
    )
    plan.add_write(
        package_path / "core" / "user" / "delivery" / "fastapi" / "controllers.py",
        content=_custom_auth_user_controller(package_name=package_name),
        detail="Remove built-in protected user routes",
    )
    plan.add_write(
        plan.repo_root / "tests" / "integration" / "conftest.py",
        content=_custom_auth_integration_conftest(package_name=package_name),
        detail="Remove built-in auth test environment setup",
    )
    plan.add_write(
        plan.repo_root / "tests" / "integration" / "factories.py",
        content=_test_factories_without_jwt(package_name=package_name),
        detail="Remove JWT test client helper",
    )
    plan.add_write(
        plan.repo_root
        / "tests"
        / "integration"
        / "core"
        / "user"
        / "delivery"
        / "fastapi"
        / "test_controllers.py",
        content=_custom_auth_user_controller_test(package_name=package_name),
        detail="Keep only public user controller tests",
    )


def _package_path(*, plan: FilePlan, answers: SetupAnswers) -> Path:
    return plan.repo_root / "src" / answers.package_name


def _django_settings_without_authentication_app(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> str:
    source_path = (
        plan.repo_root / "src" / current_package_name / "infrastructure" / "django" / "settings.py"
    )
    content = source_path.read_text(encoding="utf-8")
    content = rewrite_python_imports(
        source=content,
        old_package_name=current_package_name,
        new_package_name=answers.package_name,
    )
    content = _replace_text_references(
        text=content,
        answers=answers,
        current_package_name=current_package_name,
    )
    authentication_app = f'"{answers.package_name}.core.authentication.apps.AuthenticationConfig",'
    lines = [line for line in content.splitlines() if authentication_app not in line]

    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


def _user_model_without_refresh_sessions() -> str:
    return _dedent(
        """
        from django.contrib.auth.models import AbstractUser
        from django.db import models


        class User(AbstractUser):
            email = models.EmailField(verbose_name="email address", unique=True)

            def __str__(self) -> str:
                return f"User(id={self.pk}, username={self.username})"
        """,
    )


def _static_api_key_auth_module(*, package_name: str) -> str:
    return _dedent(
        f"""
        import secrets
        from dataclasses import dataclass
        from http import HTTPStatus

        from diwire import Injected
        from fastapi import HTTPException
        from fastapi.requests import Request
        from fastapi.security import APIKeyHeader
        from pydantic import BaseModel, ConfigDict, EmailStr, Field
        from pydantic_settings import BaseSettings, SettingsConfigDict
        from starlette.datastructures import State

        from {package_name}.foundation.factories import BaseFactory


        class StaticAPIKeyPrincipal(BaseModel):
            model_config = ConfigDict(frozen=True)

            id: int
            username: str
            email: EmailStr
            first_name: str = ""
            last_name: str = ""
            is_staff: bool = False
            is_superuser: bool = False

            @property
            def pk(self) -> int:
                return self.id


        class StaticAPIKeyRegistrySettings(BaseSettings):
            model_config = SettingsConfigDict(populate_by_name=True)

            api_keys: dict[str, StaticAPIKeyPrincipal] = Field(
                default_factory=dict,
                validation_alias="STATIC_API_KEYS",
            )

            def get_principal_for_api_key(
                self,
                *,
                api_key: str,
            ) -> StaticAPIKeyPrincipal | None:
                for registered_api_key, principal in self.api_keys.items():
                    if secrets.compare_digest(api_key, registered_api_key):
                        return principal

                return None


        class AuthenticatedRequestState(State):
            user: StaticAPIKeyPrincipal


        class AuthenticatedRequest(Request):
            state: AuthenticatedRequestState


        @dataclass(kw_only=True)
        class StaticAPIKeyAuthFactory(BaseFactory):
            _settings: Injected[StaticAPIKeyRegistrySettings]

            def __call__(
                self,
                *,
                require_staff: bool = False,
                require_superuser: bool = False,
            ) -> StaticAPIKeyAuth:
                return StaticAPIKeyAuth(
                    settings=self._settings,
                    require_staff=require_staff,
                    require_superuser=require_superuser,
                )


        class StaticAPIKeyAuth(APIKeyHeader):
            def __init__(
                self,
                settings: StaticAPIKeyRegistrySettings,
                *,
                require_staff: bool = False,
                require_superuser: bool = False,
            ) -> None:
                super().__init__(name="X-API-Key", auto_error=False)
                self._settings = settings
                self._require_staff = require_staff
                self._require_superuser = require_superuser

            async def __call__(self, request: Request) -> str | None:
                api_key = await super().__call__(request)
                if api_key is None:
                    raise HTTPException(
                        status_code=HTTPStatus.UNAUTHORIZED,
                        detail="API key is required",
                    )

                principal = self._settings.get_principal_for_api_key(api_key=api_key)
                if principal is None:
                    raise HTTPException(
                        status_code=HTTPStatus.UNAUTHORIZED,
                        detail="Invalid API key",
                    )

                self._check_permissions(principal=principal)
                request.state.user = principal

                return api_key

            def _check_permissions(self, *, principal: StaticAPIKeyPrincipal) -> None:
                if self._require_staff and not principal.is_staff:
                    raise HTTPException(
                        status_code=HTTPStatus.FORBIDDEN,
                        detail="Staff access required",
                    )

                if self._require_superuser and not principal.is_superuser:
                    raise HTTPException(
                        status_code=HTTPStatus.FORBIDDEN,
                        detail="Superuser access required",
                    )
        """,
    )


def _fastapi_factory_without_token_routes(*, package_name: str) -> str:
    return _dedent(
        f"""
        from collections.abc import AsyncIterator
        from contextlib import asynccontextmanager
        from dataclasses import dataclass
        from typing import cast

        from a2wsgi import WSGIMiddleware
        from a2wsgi.wsgi_typing import WSGIApp
        from diwire import Injected
        from fastapi import APIRouter, FastAPI
        from pydantic import Field
        from pydantic_settings import BaseSettings, SettingsConfigDict
        from starlette.middleware.cors import CORSMiddleware
        from starlette.middleware.trustedhost import TrustedHostMiddleware
        from starlette.types import ASGIApp

        from {package_name}.core.health.delivery.fastapi.controllers import HealthController
        from {package_name}.core.user.delivery.fastapi.controllers import UserController
        from {package_name}.entrypoints.django.factories import DjangoWSGIFactory
        from {package_name}.foundation.factories import BaseFactory
        from {package_name}.infrastructure.anyio.configurator import AnyIOConfigurator
        from {package_name}.infrastructure.django.middleware import (
            DjangoDatabaseConnectionMiddleware,
        )
        from {package_name}.infrastructure.logfire.instrumentor import OpenTelemetryInstrumentor
        from {package_name}.infrastructure.shared import ApplicationSettings, Environment


        class FastAPISettings(BaseSettings):
            allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])


        class CORSSettings(BaseSettings):
            model_config = SettingsConfigDict(env_prefix="CORS_")

            allow_credentials: bool = True
            allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost"])
            allow_methods: list[str] = Field(default_factory=lambda: ["*"])
            allow_headers: list[str] = Field(default_factory=lambda: ["*"])


        @dataclass(kw_only=True)
        class Lifespan:
            _anyio_configurator: Injected[AnyIOConfigurator]

            @asynccontextmanager
            async def __call__(self, _app: FastAPI) -> AsyncIterator[None]:
                self._anyio_configurator.configure()

                yield


        @dataclass(kw_only=True)
        class FastAPIFactory(BaseFactory):
            _application_settings: Injected[ApplicationSettings]
            _fastapi_settings: Injected[FastAPISettings]
            _cors_settings: Injected[CORSSettings]

            _lifespan: Injected[Lifespan]
            _telemetry_instrumentor: Injected[OpenTelemetryInstrumentor]
            _django_wsgi_factory: Injected[DjangoWSGIFactory]

            _health_controller: Injected[HealthController]
            _user_controller: Injected[UserController]

            def __call__(
                self,
                *,
                include_django: bool = True,
                add_trusted_hosts_middleware: bool = True,
                add_cors_middleware: bool = True,
            ) -> FastAPI:
                docs_url = (
                    "/docs"
                    if self._application_settings.environment != Environment.PRODUCTION
                    else None
                )

                app = FastAPI(
                    title="API",
                    lifespan=self._lifespan,
                    docs_url=docs_url,
                    redoc_url=None,
                )

                self._telemetry_instrumentor.instrument_fastapi(app=app)
                self._add_middlewares(
                    app=app,
                    add_trusted_hosts_middleware=add_trusted_hosts_middleware,
                    add_cors_middleware=add_cors_middleware,
                )
                self._register_controllers(app=app)

                if include_django:
                    django_wsgi = cast(WSGIApp, self._django_wsgi_factory())
                    django_asgi = cast(ASGIApp, WSGIMiddleware(django_wsgi))
                    app.mount("/django", django_asgi)

                return app

            def _add_middlewares(
                self,
                app: FastAPI,
                *,
                add_trusted_hosts_middleware: bool = True,
                add_cors_middleware: bool = True,
            ) -> None:
                app.add_middleware(DjangoDatabaseConnectionMiddleware)

                if add_trusted_hosts_middleware:
                    app.add_middleware(
                        TrustedHostMiddleware,
                        allowed_hosts=self._fastapi_settings.allowed_hosts,
                    )

                if add_cors_middleware:
                    app.add_middleware(
                        CORSMiddleware,
                        allow_origins=self._cors_settings.allow_origins,
                        allow_credentials=self._cors_settings.allow_credentials,
                        allow_methods=self._cors_settings.allow_methods,
                        allow_headers=self._cors_settings.allow_headers,
                    )

            def _register_controllers(
                self,
                app: FastAPI,
            ) -> None:
                health_router = APIRouter(tags=["health"])
                self._health_controller.register(health_router)
                app.include_router(health_router)

                user_router = APIRouter(tags=["user"])
                self._user_controller.register(user_router)
                app.include_router(user_router)
        """,
    )


def _static_api_key_user_controller(*, package_name: str) -> str:
    return _dedent(
        f"""
        from dataclasses import dataclass
        from http import HTTPStatus
        from typing import Any

        from diwire import Injected
        from fastapi import APIRouter, Depends, HTTPException

        from {package_name}.core.authentication.delivery.fastapi.auth import (
            AuthenticatedRequest,
            StaticAPIKeyAuthFactory,
        )
        from {package_name}.core.user.delivery.fastapi.schemas import (
            CreateUserRequestSchema,
            UserSchema,
        )
        from {package_name}.core.user.use_cases import UserUseCase
        from {package_name}.foundation.delivery.controllers import BaseAsyncController


        @dataclass(kw_only=True)
        class UserController(BaseAsyncController):
            _static_api_key_auth_factory: Injected[StaticAPIKeyAuthFactory]
            _user_use_case: Injected[UserUseCase]

            def __post_init__(self) -> None:
                self._auth = self._static_api_key_auth_factory()
                self._staff_auth = self._static_api_key_auth_factory(require_staff=True)
                super().__post_init__()

            def register(self, registry: APIRouter) -> None:
                registry.add_api_route(
                    path="/v1/users/",
                    endpoint=self.create_user,
                    methods=["POST"],
                    response_model=UserSchema,
                )

                registry.add_api_route(
                    path="/v1/users/me",
                    endpoint=self.get_current_user,
                    methods=["GET"],
                    dependencies=[Depends(self._auth)],
                    response_model=UserSchema,
                )

                registry.add_api_route(
                    path="/v1/users/{{user_id}}",
                    endpoint=self.get_user_by_id,
                    methods=["GET"],
                    dependencies=[Depends(self._staff_auth)],
                    response_model=UserSchema,
                )

            async def create_user(self, request_body: CreateUserRequestSchema) -> UserSchema:
                user = await self._user_use_case.create_user(data=request_body)

                return UserSchema.model_validate(user, from_attributes=True)

            async def get_current_user(self, request: AuthenticatedRequest) -> UserSchema:
                return UserSchema.model_validate(request.state.user, from_attributes=True)

            async def get_user_by_id(
                self,
                user_id: int,
            ) -> UserSchema:
                user = await self._user_use_case.get_user_by_id(user_id=user_id)
                if user is None:
                    raise HTTPException(
                        status_code=HTTPStatus.NOT_FOUND,
                        detail="User not found",
                    )

                return UserSchema.model_validate(user, from_attributes=True)

            async def handle_exception(self, exception: Exception) -> Any:
                if isinstance(exception, UserUseCase.WEAK_PASSWORD_ERROR):
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST,
                        detail="Password does not meet the strength requirements",
                    ) from exception

                if isinstance(exception, UserUseCase.USER_ALREADY_EXISTS_ERROR):
                    raise HTTPException(
                        status_code=HTTPStatus.CONFLICT,
                        detail="A user with the given username or email already exists",
                    ) from exception

                return await super().handle_exception(exception)
        """,
    )


def _custom_auth_user_controller(*, package_name: str) -> str:
    return _dedent(
        f"""
        from dataclasses import dataclass
        from http import HTTPStatus
        from typing import Any

        from diwire import Injected
        from fastapi import APIRouter, HTTPException

        from {package_name}.core.user.delivery.fastapi.schemas import (
            CreateUserRequestSchema,
            UserSchema,
        )
        from {package_name}.core.user.use_cases import UserUseCase
        from {package_name}.foundation.delivery.controllers import BaseAsyncController


        @dataclass(kw_only=True)
        class UserController(BaseAsyncController):
            _user_use_case: Injected[UserUseCase]

            def register(self, registry: APIRouter) -> None:
                registry.add_api_route(
                    path="/v1/users/",
                    endpoint=self.create_user,
                    methods=["POST"],
                    response_model=UserSchema,
                )

            async def create_user(self, request_body: CreateUserRequestSchema) -> UserSchema:
                user = await self._user_use_case.create_user(data=request_body)

                return UserSchema.model_validate(user, from_attributes=True)

            async def handle_exception(self, exception: Exception) -> Any:
                if isinstance(exception, UserUseCase.WEAK_PASSWORD_ERROR):
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST,
                        detail="Password does not meet the strength requirements",
                    ) from exception

                if isinstance(exception, UserUseCase.USER_ALREADY_EXISTS_ERROR):
                    raise HTTPException(
                        status_code=HTTPStatus.CONFLICT,
                        detail="A user with the given username or email already exists",
                    ) from exception

                return await super().handle_exception(exception)
        """,
    )


def _static_api_key_integration_conftest(*, package_name: str) -> str:
    return _dedent(
        f"""
        import pytest
        from diwire import Container
        from throttled.asyncio import MemoryStore

        from {package_name}.infrastructure.throttled.throttler import AsyncThrottlerStoreFactory
        from {package_name}.ioc.container import get_container
        from tests.integration.factories import (
            TestCeleryWorkerFactory,
            TestClientFactory,
            TestTasksRegistryFactory,
            TestUserFactory,
        )

        _STATIC_API_KEYS = (
            '{{"test-static-api-key":{{"id":1,"username":"test-static-api-key",'
            '"email":"test-static-api-key@example.com","first_name":"Test",'
            '"last_name":"API Key","is_staff":true,"is_superuser":false}}}}'
        )


        @pytest.fixture(scope="function")
        def container(monkeypatch: pytest.MonkeyPatch) -> Container:
            monkeypatch.setenv("STATIC_API_KEYS", _STATIC_API_KEYS)
            container = get_container()
            container.add_instance(lambda: MemoryStore(), provides=AsyncThrottlerStoreFactory)  # noqa: PLW0108

            return container


        # region Factories


        @pytest.fixture(scope="function")
        def test_client_factory(container: Container) -> TestClientFactory:
            return TestClientFactory(container=container)


        @pytest.fixture(scope="function")
        def user_factory(
            transactional_db: None,
            container: Container,
        ) -> TestUserFactory:
            return TestUserFactory(container=container)


        @pytest.fixture(scope="function")
        def celery_worker_factory(container: Container) -> TestCeleryWorkerFactory:
            return TestCeleryWorkerFactory(container=container)


        @pytest.fixture(scope="function")
        def tasks_registry_factory(container: Container) -> TestTasksRegistryFactory:
            return TestTasksRegistryFactory(container=container)


        # endregion Factories
        """,
    )


def _custom_auth_integration_conftest(*, package_name: str) -> str:
    return _dedent(
        f"""
        import pytest
        from diwire import Container
        from throttled.asyncio import MemoryStore

        from {package_name}.infrastructure.throttled.throttler import AsyncThrottlerStoreFactory
        from {package_name}.ioc.container import get_container
        from tests.integration.factories import (
            TestCeleryWorkerFactory,
            TestClientFactory,
            TestTasksRegistryFactory,
            TestUserFactory,
        )


        @pytest.fixture(scope="function")
        def container() -> Container:
            container = get_container()
            container.add_instance(lambda: MemoryStore(), provides=AsyncThrottlerStoreFactory)  # noqa: PLW0108

            return container


        # region Factories


        @pytest.fixture(scope="function")
        def test_client_factory(container: Container) -> TestClientFactory:
            return TestClientFactory(container=container)


        @pytest.fixture(scope="function")
        def user_factory(
            transactional_db: None,
            container: Container,
        ) -> TestUserFactory:
            return TestUserFactory(container=container)


        @pytest.fixture(scope="function")
        def celery_worker_factory(container: Container) -> TestCeleryWorkerFactory:
            return TestCeleryWorkerFactory(container=container)


        @pytest.fixture(scope="function")
        def tasks_registry_factory(container: Container) -> TestTasksRegistryFactory:
            return TestTasksRegistryFactory(container=container)


        # endregion Factories
        """,
    )


def _test_factories_without_jwt(*, package_name: str) -> str:
    return _dedent(
        f"""
        from contextlib import AbstractContextManager
        from typing import Any

        from celery import Celery
        from celery.contrib.testing import worker
        from celery.worker import WorkController
        from fastapi.testclient import TestClient

        from {package_name}.core.user.models import User
        from {package_name}.entrypoints.celery.factories import CeleryAppFactory
        from {package_name}.entrypoints.celery.registry import TasksRegistry
        from {package_name}.entrypoints.fastapi.factories import FastAPIFactory
        from tests.foundation.factories import ContainerBasedFactory


        class TestClientFactory(ContainerBasedFactory):
            def __call__(
                self,
                headers: dict[str, str] | None = None,
                **kwargs: Any,
            ) -> TestClient:
                api_factory = self._container.resolve(FastAPIFactory)

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
                email: str | None = None,
                *,
                is_staff: bool = False,
                **kwargs: Any,
            ) -> User:
                email = email or f"{{username}}@test.com"

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
                celery_app = celery_app_factory()
                configure_celery_app_for_tests(celery_app)

                return worker.start_worker(
                    app=celery_app,
                    perform_ping_check=False,
                )


        class TestTasksRegistryFactory(ContainerBasedFactory):
            def __call__(self) -> TasksRegistry:
                celery_app_factory = self._container.resolve(CeleryAppFactory)
                configure_celery_app_for_tests(celery_app_factory())

                return self._container.resolve(TasksRegistry)


        def configure_celery_app_for_tests(celery_app: Celery) -> None:
            celery_app.conf.update(
                broker_url="memory://",
                result_backend="cache+memory://",
            )
        """,
    )


def _static_api_key_integration_auth_test(*, package_name: str) -> str:
    return _dedent(
        f"""
        from http import HTTPStatus

        import pytest

        from {package_name}.core.user.delivery.fastapi.schemas import UserSchema
        from tests.integration.factories import TestClientFactory

        _TEST_API_KEY = "test-static-api-key"  # noqa: S105


        @pytest.mark.django_db(transaction=True)
        def test_static_api_key_authenticates_current_user_and_skips_token_routes(
            test_client_factory: TestClientFactory,
        ) -> None:
            with test_client_factory(headers={{"X-API-Key": _TEST_API_KEY}}) as test_client:
                user_response = test_client.get("/v1/users/me")
                token_response = test_client.post(
                    "/v1/auth/token",
                    json={{"username": "service", "password": "unused"}},
                )

            user_data = UserSchema.model_validate(user_response.json())
            assert user_response.status_code == HTTPStatus.OK
            assert user_data.id == 1
            assert user_data.username == "test-static-api-key"
            assert token_response.status_code == HTTPStatus.NOT_FOUND
        """,
    )


def _static_api_key_unit_auth_test(*, package_name: str) -> str:
    return _dedent(
        f"""
        from http import HTTPStatus

        import pytest
        from fastapi import HTTPException
        from starlette.requests import Request
        from starlette.types import Scope

        from {package_name}.core.authentication.delivery.fastapi.auth import (
            StaticAPIKeyAuth,
            StaticAPIKeyPrincipal,
            StaticAPIKeyRegistrySettings,
        )


        def test_static_api_key_registry_parses_json_environment(
            monkeypatch: pytest.MonkeyPatch,
        ) -> None:
            monkeypatch.setenv(
                "STATIC_API_KEYS",
                (
                    '{{"env-key":{{"id":7,"username":"service","email":"service@example.com",'
                    '"is_staff":true,"is_superuser":false}}}}'
                ),
            )

            settings = StaticAPIKeyRegistrySettings()

            principal = settings.get_principal_for_api_key(api_key="env-key")
            assert principal is not None
            assert principal.pk == 7
            assert principal.username == "service"
            assert principal.is_staff is True


        @pytest.mark.anyio
        async def test_static_api_key_auth_sets_request_user() -> None:
            settings = _settings(is_staff=True)
            request = _request(headers={{"X-API-Key": "valid-key"}})
            auth = StaticAPIKeyAuth(settings=settings)

            api_key = await auth(request)

            assert api_key == "valid-key"
            assert request.state.user.username == "service"
            assert request.state.user.pk == 1


        @pytest.mark.anyio
        async def test_static_api_key_auth_rejects_missing_key() -> None:
            auth = StaticAPIKeyAuth(settings=_settings())

            with pytest.raises(HTTPException) as error:
                await auth(_request())

            assert error.value.status_code == HTTPStatus.UNAUTHORIZED
            assert error.value.detail == "API key is required"


        @pytest.mark.anyio
        async def test_static_api_key_auth_rejects_invalid_key() -> None:
            auth = StaticAPIKeyAuth(settings=_settings())

            with pytest.raises(HTTPException) as error:
                await auth(_request(headers={{"X-API-Key": "invalid-key"}}))

            assert error.value.status_code == HTTPStatus.UNAUTHORIZED
            assert error.value.detail == "Invalid API key"


        @pytest.mark.anyio
        async def test_static_api_key_auth_checks_staff_permission() -> None:
            auth = StaticAPIKeyAuth(settings=_settings(is_staff=False), require_staff=True)

            with pytest.raises(HTTPException) as error:
                await auth(_request(headers={{"X-API-Key": "valid-key"}}))

            assert error.value.status_code == HTTPStatus.FORBIDDEN
            assert error.value.detail == "Staff access required"


        def _settings(*, is_staff: bool = False) -> StaticAPIKeyRegistrySettings:
            return StaticAPIKeyRegistrySettings(
                api_keys={{
                    "valid-key": StaticAPIKeyPrincipal(
                        id=1,
                        username="service",
                        email="service@example.com",
                        is_staff=is_staff,
                        is_superuser=False,
                    ),
                }},
            )


        def _request(*, headers: dict[str, str] | None = None) -> Request:
            header_items = [
                (key.lower().encode(), value.encode()) for key, value in (headers or {{}}).items()
            ]
            scope: Scope = {{
                "type": "http",
                "method": "GET",
                "path": "/",
                "raw_path": b"/",
                "query_string": b"",
                "headers": header_items,
                "client": ("testclient", 50000),
                "server": ("testserver", 80),
                "scheme": "http",
            }}
            return Request(scope)
        """,
    )


def _static_api_key_user_controller_test(*, package_name: str) -> str:
    return _dedent(
        f"""
        from http import HTTPStatus

        import pytest

        from {package_name}.core.user.delivery.fastapi.schemas import UserSchema
        from {package_name}.core.user.models import User
        from tests.integration.factories import TestClientFactory, TestUserFactory

        _TEST_API_KEY = "test-static-api-key"  # noqa: S105
        _TEST_PASSWORD = "test-password"  # noqa: S105


        @pytest.fixture(scope="function")
        def user(user_factory: TestUserFactory) -> User:
            return user_factory(username="test", password=_TEST_PASSWORD)


        @pytest.mark.django_db(transaction=True)
        class TestUserController:
            def test_create_user(self, test_client_factory: TestClientFactory) -> None:
                with test_client_factory() as test_client:
                    response = test_client.post(
                        "/v1/users/",
                        json={{
                            "username": "test_new_user",
                            "email": "new_user@test.com",
                            "password": _TEST_PASSWORD,
                            "first_name": "Test",
                            "last_name": "User",
                        }},
                    )

                response_data = UserSchema.model_validate(response.json())
                assert response.status_code == HTTPStatus.OK
                assert response_data.username == "test_new_user"

            def test_auth_for_static_api_key(
                self,
                test_client_factory: TestClientFactory,
            ) -> None:
                with test_client_factory(headers={{"X-API-Key": _TEST_API_KEY}}) as test_client:
                    response = test_client.get("/v1/users/me")

                user_data = UserSchema.model_validate(response.json())
                assert response.status_code == HTTPStatus.OK
                assert user_data.username == "test-static-api-key"

            def test_staff_static_api_key_for_user(
                self,
                test_client_factory: TestClientFactory,
                user_factory: TestUserFactory,
            ) -> None:
                other_user = user_factory(username="other_user")
                with test_client_factory(headers={{"X-API-Key": _TEST_API_KEY}}) as test_client:
                    response = test_client.get(f"/v1/users/{{other_user.pk}}")

                assert response.status_code == HTTPStatus.OK
        """,
    )


def _custom_auth_user_controller_test(*, package_name: str) -> str:
    return _dedent(
        f"""
        from http import HTTPStatus

        import pytest

        from {package_name}.core.user.delivery.fastapi.schemas import UserSchema
        from tests.integration.factories import TestClientFactory

        _TEST_PASSWORD = "test-password"  # noqa: S105


        @pytest.mark.django_db(transaction=True)
        class TestUserController:
            def test_create_user(self, test_client_factory: TestClientFactory) -> None:
                with test_client_factory() as test_client:
                    response = test_client.post(
                        "/v1/users/",
                        json={{
                            "username": "test_new_user",
                            "email": "new_user@test.com",
                            "password": _TEST_PASSWORD,
                            "first_name": "Test",
                            "last_name": "User",
                        }},
                    )

                response_data = UserSchema.model_validate(response.json())
                assert response.status_code == HTTPStatus.OK
                assert response_data.username == "test_new_user"
        """,
    )


def _plan_config_rewrites(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    _rewrite_config_file(
        plan=plan,
        relative_path="pyproject.toml",
        rewrite=lambda content: update_pyproject_toml(
            content,
            answers=answers,
            old_package_name=current_package_name,
        ),
    )
    _rewrite_config_file(
        plan=plan,
        relative_path="ruff.toml",
        rewrite=lambda content: update_ruff_toml(content, package_name=answers.package_name),
    )
    _rewrite_config_file(plan=plan, relative_path="prek.toml", rewrite=update_prek_toml)
    _rewrite_config_file(
        plan=plan,
        relative_path="docker/docker-compose.yaml",
        rewrite=lambda content: update_docker_compose_yaml(
            content,
            answers=answers,
            old_package_name=current_package_name,
            is_local_overlay=False,
        ),
    )
    _rewrite_config_file(
        plan=plan,
        relative_path="docker/docker-compose.local.yaml",
        rewrite=lambda content: update_docker_compose_yaml(
            content,
            answers=answers,
            old_package_name=current_package_name,
            is_local_overlay=True,
        ),
    )
    _rewrite_config_file(
        plan=plan,
        relative_path="docker/docker-compose.test.yaml",
        rewrite=lambda content: update_docker_compose_yaml(
            content,
            answers=answers,
            old_package_name=current_package_name,
            is_local_overlay=True,
        ),
    )
    _rewrite_makefile(plan=plan, answers=answers, current_package_name=current_package_name)


def _plan_environment_files(*, plan: FilePlan, answers: SetupAnswers) -> None:
    env_path = plan.repo_root / ".env"
    if answers.overwrite_env or not env_path.exists():
        plan.add_write(
            env_path,
            content=build_env_content(answers=answers),
            detail="Write generated .env",
        )

    plan.add_write(
        plan.repo_root / ".env.example",
        content=build_env_example_content(answers=answers),
        detail="Update .env.example",
    )
    plan.add_write(
        plan.repo_root / ".env.test.example",
        content=build_test_env_example_content(answers=answers),
        detail="Update .env.test.example",
    )


def _plan_docs(*, plan: FilePlan, answers: SetupAnswers, current_package_name: str) -> None:
    readme_path = plan.repo_root / "README.md"
    if readme_path.exists():
        plan.add_write(
            readme_path,
            content=build_project_readme(answers=answers),
            detail="Rewrite README for generated project",
        )

    docs_path = plan.repo_root / "docs"
    if not answers.keep_docs:
        plan.add_delete(docs_path, detail="Remove documentation")
        return

    _rewrite_docs_files(plan=plan, answers=answers, current_package_name=current_package_name)


def _plan_self_delete(*, plan: FilePlan, answers: SetupAnswers) -> None:
    if not answers.delete_wizard:
        return

    plan.add_delete(plan.repo_root / "management" / "setup_wizard", detail="Remove setup wizard")
    plan.add_delete(plan.repo_root / "tests" / "setup_wizard", detail="Remove setup wizard tests")


def _rewrite_config_file(
    *,
    plan: FilePlan,
    relative_path: str,
    rewrite: ConfigRewrite,
) -> None:
    path = plan.repo_root / relative_path
    if not path.exists():
        return

    plan.add_write(
        path,
        content=rewrite(path.read_text(encoding="utf-8")),
        detail=f"Update {relative_path}",
    )


def _rewrite_makefile(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    path = plan.repo_root / "Makefile"
    if not path.exists():
        return

    content = _replace_text_references(
        text=path.read_text(encoding="utf-8"),
        answers=answers,
        current_package_name=current_package_name,
    )
    content = (
        _ensure_setup_target(content)
        if not answers.delete_wizard
        else _remove_setup_target(content)
    )
    content = _remove_docs_targets(content) if not answers.keep_docs else content
    plan.add_write(path, content=content, detail="Update Makefile")


def _rewrite_docs_files(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    mkdocs_path = plan.repo_root / "docs" / "mkdocs.yml"
    if mkdocs_path.exists():
        plan.add_write(
            mkdocs_path,
            content=update_mkdocs_yaml(
                mkdocs_path.read_text(encoding="utf-8"),
                answers=answers,
                old_package_name=current_package_name,
            ),
            detail="Update MkDocs config",
        )

    for path in (plan.repo_root / "docs").rglob("*"):
        if not path.is_file() or path == mkdocs_path:
            continue
        if path.suffix not in {".md", ".yml", ".yaml", ".txt"} and path.name != "CNAME":
            continue

        if path.name == "CNAME" and answers.docs_site_url is None:
            plan.add_delete(path, detail="Remove docs custom domain")
            continue

        content = _replace_text_references(
            text=path.read_text(encoding="utf-8"),
            answers=answers,
            current_package_name=current_package_name,
        )
        if path.name == "CNAME" and answers.docs_site_url is not None:
            content = f"{urlsplit(answers.docs_site_url).netloc}\n"
        plan.add_write(path, content=content, detail=f"Update {plan.relative_path(path)}")


def _iter_python_files(*, repo_root: Path, answers: SetupAnswers) -> list[Path]:
    paths: list[Path] = []
    for base_path in (repo_root / "src", repo_root / "tests", repo_root / "management"):
        if not base_path.exists():
            continue
        for path in base_path.rglob("*.py"):
            if _is_excluded_path(path=path):
                continue
            if answers.delete_wizard and _is_wizard_path(path=path, repo_root=repo_root):
                continue
            paths.append(path)

    return paths


def _target_path_for_package_rename(
    *,
    source_path: Path,
    repo_root: Path,
    current_package_name: str,
    new_package_name: str,
) -> Path:
    old_package_root = repo_root / "src" / current_package_name
    try:
        return repo_root / "src" / new_package_name / source_path.relative_to(old_package_root)
    except ValueError:
        return source_path


def _replace_text_references(
    *,
    text: str,
    answers: SetupAnswers,
    current_package_name: str,
) -> str:
    return replace_project_references(
        text=text,
        references=ProjectReferences(
            old_package_name=current_package_name,
            new_package_name=answers.package_name,
            project_name=answers.project_name,
            docs_site_url=answers.docs_site_url,
            repo_url=answers.repo_url,
        ),
    )


def _ensure_setup_target(content: str) -> str:
    if "\nsetup:\n" in content:
        return content

    return (
        content.rstrip()
        + "\n\nsetup:\n\tuv run --group setup python -m management.setup_wizard $(ARGS)\n"
    )


def _remove_setup_target(content: str) -> str:
    content = re.sub(
        pattern=r"\nsetup:\n\tuv run --group setup python -m management\.setup_wizard \$\(ARGS\)\n",
        repl="\n",
        string=content,
    )
    return content.replace(" setup ", " ").replace(" setup\n", "\n")


def _remove_docs_targets(content: str) -> str:
    content = re.sub(
        pattern=r"\n(?:\.PHONY: docs docs-build\n)?docs:\n\t.*\n",
        repl="\n",
        string=content,
    )
    content = re.sub(pattern=r"\ndocs-build:\n\t.*\n", repl="\n", string=content)
    return content.replace(" docs docs-build", "")


def _is_python_package(path: Path) -> bool:
    return path.is_dir() and (path / "__init__.py").exists()


def _is_excluded_path(*, path: Path) -> bool:
    return any(part in EXCLUDED_DIR_NAMES for part in path.parts)


def _is_wizard_path(*, path: Path, repo_root: Path) -> bool:
    for wizard_path in (
        repo_root / "management" / "setup_wizard",
        repo_root / "tests" / "setup_wizard",
    ):
        try:
            path.relative_to(wizard_path)
        except ValueError:
            continue

        return True

    return False


def _dedent(value: str) -> str:
    return textwrap.dedent(value).lstrip()


type ConfigRewrite = Callable[[str], str]
