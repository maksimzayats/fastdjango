from __future__ import annotations

import ast
import textwrap
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from management.setup_wizard.models import (
    AuthenticationMode,
    DatabaseMode,
    RedisMode,
    SetupAnswers,
    StorageMode,
)
from management.setup_wizard.planner import build_setup_plan


def test_full_package_rename_rewrites_imports_config_and_docs(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(
        project_name="Acme API",
        package_name="acme_api",
        distribution_name="acme-api",
        docs_site_url="https://docs.example.com",
        storage_mode=StorageMode.MINIO,
        delete_wizard=False,
    )

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    assert not (tmp_path / "src" / "fastdjango").exists()
    renamed_module = tmp_path / "src" / "acme_api" / "core" / "sample.py"
    assert "from acme_api.foundation.services import BaseService" in renamed_module.read_text()

    pyproject = _read_toml(tmp_path / "pyproject.toml")
    assert pyproject["project"]["name"] == "acme-api"
    assert pyproject["tool"]["django-stubs"]["django_settings_module"] == (
        "acme_api.infrastructure.django.settings"
    )
    assert pyproject["dependency-groups"]["docs"] == ["mkdocs"]
    assert pyproject["dependency-groups"]["setup"] == ["questionary"]

    ruff = _read_toml(tmp_path / "ruff.toml")
    assert ruff["lint"]["isort"]["known-first-party"] == ["acme_api"]

    docs_index = (tmp_path / "docs" / "en" / "index.md").read_text()
    assert "src/acme_api/core/sample.py" in docs_index
    assert "https://docs.example.com" in (tmp_path / "docs" / "mkdocs.yml").read_text()
    assert (tmp_path / "docs" / "en" / "CNAME").read_text() == "docs.example.com\n"


def test_blank_docs_site_url_keeps_docs_local_only(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(
        project_name="Acme API",
        package_name="acme_api",
        distribution_name="acme-api",
        docs_site_url=None,
        delete_wizard=False,
    )

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    assert "site_url" not in (tmp_path / "docs" / "mkdocs.yml").read_text()
    assert not (tmp_path / "docs" / "en" / "CNAME").exists()
    assert "[local docs](docs/en)" in (tmp_path / "README.md").read_text()
    assert (
        "github.com/maksimzayats/fastdjango"
        not in (tmp_path / "docs" / "en" / "index.md").read_text()
    )


def test_local_storage_prunes_minio_compose_services(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(storage_mode=StorageMode.LOCAL, delete_wizard=False)

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    compose = (tmp_path / "docker" / "docker-compose.yaml").read_text()
    local_overlay = (tmp_path / "docker" / "docker-compose.local.yaml").read_text()

    assert "minio:" not in compose
    assert "minio-create-buckets" not in compose
    assert "minio_data" not in compose
    assert "AWS_S3_ENDPOINT_URL" not in compose
    assert "minio:" not in local_overlay


def test_sqlite_database_prunes_postgres_compose_services(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(database_mode=DatabaseMode.SQLITE, delete_wizard=False)

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    compose = (tmp_path / "docker" / "docker-compose.yaml").read_text()
    env_content = (tmp_path / ".env").read_text()

    assert "postgres:" not in compose
    assert "pgbouncer:" not in compose
    assert "postgres_data" not in compose
    assert "DATABASE_URL: " not in compose
    assert "DATABASE_URL=sqlite:///db.sqlite3" in env_content
    assert "POSTGRES_PASSWORD" not in env_content


def test_remote_postgres_writes_placeholder_example_and_real_env(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(
        database_mode=DatabaseMode.REMOTE_POSTGRES,
        database_url="postgres://real:secret@db.example.com:5432/app",
        delete_wizard=False,
    )

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    env_content = (tmp_path / ".env").read_text()
    env_example_content = (tmp_path / ".env.example").read_text()

    assert 'DATABASE_URL="postgres://real:secret@db.example.com:5432/app"' in env_content
    assert "postgres://user:password@db.example.com:5432/example_api" in env_example_content
    assert "real:secret" not in env_example_content


def test_remote_redis_prunes_redis_compose_service(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(
        redis_mode=RedisMode.REMOTE_REDIS,
        redis_url="redis://default:secret@redis.example.com:6379/0",
        delete_wizard=False,
    )

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    compose = (tmp_path / "docker" / "docker-compose.yaml").read_text()
    env_content = (tmp_path / ".env").read_text()
    env_example_content = (tmp_path / ".env.example").read_text()

    assert "redis:" not in compose
    assert "redis_data" not in compose
    assert "REDIS_URL: " not in compose
    assert 'REDIS_URL="redis://default:secret@redis.example.com:6379/0"' in env_content
    assert "redis://default:password@redis.example.com:6379/0" in env_example_content
    assert "default:secret" not in env_example_content


def test_remote_s3_writes_placeholders_to_examples_and_real_values_to_env(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(
        storage_mode=StorageMode.REMOTE_S3,
        delete_wizard=False,
        s3_endpoint_url="https://storage.example.com",
        s3_public_endpoint_url="https://assets.example.com",
        s3_region_name="eu-central-1",
        s3_access_key_id="real-access-key",
        s3_secret_access_key="real-secret-key",  # noqa: S106
    )

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    env_content = (tmp_path / ".env").read_text()
    env_example_content = (tmp_path / ".env.example").read_text()

    assert "AWS_S3_ENDPOINT_URL=https://storage.example.com" in env_content
    assert "AWS_S3_SECRET_ACCESS_KEY=real-secret-key" in env_content
    assert "AWS_S3_ENDPOINT_URL=https://s3.example.com" in env_example_content
    assert "real-secret-key" not in env_example_content


def test_ports_origins_logfire_and_repo_metadata_are_written(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(
        project_name="Acme API",
        package_name="acme_api",
        distribution_name="acme-api",
        storage_mode=StorageMode.MINIO,
        delete_wizard=False,
        repo_url="https://github.com/acme/acme-api",
        production_api_origin="https://api.acme.com",
        frontend_origin="https://app.acme.com",
        enable_logfire=True,
        logfire_token="real-logfire-token",  # noqa: S106
        logfire_environment="staging",
        postgres_port=15432,
        redis_port=16379,
        minio_api_port=19000,
        minio_console_port=19001,
    )

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    env_content = (tmp_path / ".env").read_text()
    env_example_content = (tmp_path / ".env.example").read_text()
    overlay = (tmp_path / "docker" / "docker-compose.local.yaml").read_text()
    mkdocs = (tmp_path / "docs" / "mkdocs.yml").read_text()
    readme = (tmp_path / "README.md").read_text()

    assert "COMPOSE_PROJECT_NAME=acme-api" in env_content
    assert 'ALLOWED_HOSTS=["127.0.0.1","localhost","0.0.0.0","api.acme.com"]' in env_content
    assert 'CORS_ALLOW_ORIGINS=["http://localhost","https://app.acme.com"]' in env_content
    assert "LOGFIRE_ENABLED=true" in env_content
    assert "LOGFIRE_TOKEN=real-logfire-token" in env_content
    assert "LOGFIRE_TOKEN=replace-me" in env_example_content
    env_values = _env_values(content=env_content)
    assert env_values["MINIO_ROOT_USER"] == env_values["AWS_S3_ACCESS_KEY_ID"]
    assert env_values["MINIO_ROOT_PASSWORD"] == env_values["AWS_S3_SECRET_ACCESS_KEY"]
    assert "MINIO_ROOT_USER=example-minio-access-key-id" in env_example_content
    assert "MINIO_ROOT_PASSWORD=example-minio-secret-access-key" in env_example_content
    assert "AWS_S3_ENDPOINT_URL=http://localhost:${MINIO_API_PORT}" in env_content
    assert "${POSTGRES_PORT:-15432}:5432" in overlay
    assert "${REDIS_PORT:-16379}:6379" in overlay
    assert "${MINIO_API_PORT:-19000}:9000" in overlay
    assert "repo_url: https://github.com/acme/acme-api" in mkdocs
    assert "repo_name: acme/acme-api" in mkdocs
    assert "Project repository: [https://github.com/acme/acme-api]" in readme
    assert (
        f"Generated from [fastdjango](https://github.com/maksimzayats/fastdjango) "
        f"on {datetime.now(tz=UTC).date().isoformat()}."
    ) in readme
    assert (
        "https://github.com/acme/acme-api/issues"
        in (tmp_path / "docs" / "en" / "index.md").read_text()
    )


def test_generated_env_files_are_grouped_by_concern(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(storage_mode=StorageMode.MINIO, delete_wizard=False)

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    env_example_content = (tmp_path / ".env.example").read_text()
    test_env_example_content = (tmp_path / ".env.test.example").read_text()

    _assert_markers_in_order(
        content=env_example_content,
        markers=(
            "# Compose\n",
            "\n# Application\n",
            "\n# Secrets\n",
            "\n# Authentication\n",
            "\n# HTTP\n",
            "\n# Observability\n",
            "\n# Database\n",
            "\n# Redis\n",
            "\n# Storage\n",
            "\n# S3\n",
        ),
    )
    _assert_markers_in_order(
        content=test_env_example_content,
        markers=(
            "# Application\n",
            "\n# Secrets\n",
            "\n# Authentication\n",
            "\n# Observability\n",
            "\n# Database\n",
            "\n# Redis\n",
            "\n# Storage\n",
        ),
    )
    assert "\n\n# Database\n" in env_example_content
    assert "\n\n# Database\n" in test_env_example_content


def test_static_api_key_authentication_writes_json_registry_without_jwt_secret(
    tmp_path: Path,
) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(
        authentication_mode=AuthenticationMode.STATIC_API_KEYS,
        delete_wizard=False,
    )

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    env_content = (tmp_path / ".env").read_text()
    env_example_content = (tmp_path / ".env.example").read_text()
    test_env_example_content = (tmp_path / ".env.test.example").read_text()
    readme = (tmp_path / "README.md").read_text()

    assert "AUTHENTICATION_MODE=static-api-keys" in env_content
    assert "JWT_SECRET_KEY" not in env_content
    assert '"local-api-key@example.com"' in env_content
    assert "AUTHENTICATION_MODE=static-api-keys" in env_example_content
    assert 'STATIC_API_KEYS={"example-static-api-key":' in env_example_content
    assert "AUTHENTICATION_MODE=static-api-keys" in test_env_example_content
    assert 'STATIC_API_KEYS={"test-static-api-key":' in test_env_example_content
    assert "- Authentication: static API keys from environment JSON" in readme


def test_static_api_key_authentication_prunes_refresh_session_code(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(
        authentication_mode=AuthenticationMode.STATIC_API_KEYS,
        delete_wizard=False,
    )

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    package_root = tmp_path / "src" / "example_api"
    auth_root = package_root / "core" / "authentication"
    auth_dependency = (auth_root / "delivery" / "fastapi" / "auth.py").read_text()
    settings = (package_root / "infrastructure" / "django" / "settings.py").read_text()
    user_model = (package_root / "core" / "user" / "models.py").read_text()
    fastapi_factory = (package_root / "entrypoints" / "fastapi" / "factories.py").read_text()
    user_controller = (
        package_root / "core" / "user" / "delivery" / "fastapi" / "controllers.py"
    ).read_text()
    test_factories = (tmp_path / "tests" / "integration" / "factories.py").read_text()

    _assert_python_files_parse(root=package_root)
    _assert_python_files_parse(root=tmp_path / "tests")

    assert "StaticAPIKeyAuth" in auth_dependency
    assert "JWTService" not in auth_dependency
    assert "JWTAuthFactory" not in auth_dependency
    assert "AuthenticationConfig" not in settings
    assert "RefreshSession" not in user_model
    assert "refresh_sessions" not in user_model
    assert "AuthenticationTokenController" not in fastapi_factory
    assert "StaticAPIKeyAuthFactory" in user_controller
    assert "JWTAuthFactory" not in user_controller
    assert "JWTService" not in test_factories
    assert not (auth_root / "models.py").exists()
    assert not (auth_root / "use_cases.py").exists()
    assert not (auth_root / "services").exists()
    assert not (auth_root / "migrations").exists()
    assert not (auth_root / "delivery" / "fastapi" / "controllers.py").exists()
    assert not (
        tmp_path
        / "tests"
        / "integration"
        / "core"
        / "authentication"
        / "delivery"
        / "fastapi"
        / "test_controllers.py"
    ).exists()
    assert not (tmp_path / "tests" / "unit" / "core" / "authentication" / "services").exists()


def test_custom_authentication_skips_generated_auth_secrets(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(
        authentication_mode=AuthenticationMode.CUSTOM,
        delete_wizard=False,
    )

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    env_content = (tmp_path / ".env").read_text()
    test_env_example_content = (tmp_path / ".env.test.example").read_text()

    assert "AUTHENTICATION_MODE=custom" in env_content
    assert "AUTHENTICATION_MODE=custom" in test_env_example_content
    assert "JWT_SECRET_KEY" not in env_content
    assert "STATIC_API_KEYS" not in env_content


def test_custom_authentication_prunes_built_in_authentication_code(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(
        authentication_mode=AuthenticationMode.CUSTOM,
        delete_wizard=False,
    )

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    package_root = tmp_path / "src" / "example_api"
    settings = (package_root / "infrastructure" / "django" / "settings.py").read_text()
    fastapi_factory = (package_root / "entrypoints" / "fastapi" / "factories.py").read_text()
    user_controller = (
        package_root / "core" / "user" / "delivery" / "fastapi" / "controllers.py"
    ).read_text()
    user_controller_test = (
        tmp_path
        / "tests"
        / "integration"
        / "core"
        / "user"
        / "delivery"
        / "fastapi"
        / "test_controllers.py"
    ).read_text()

    _assert_python_files_parse(root=package_root)
    _assert_python_files_parse(root=tmp_path / "tests")

    assert not (package_root / "core" / "authentication").exists()
    assert not (tmp_path / "tests" / "integration" / "core" / "authentication").exists()
    assert not (tmp_path / "tests" / "unit" / "core" / "authentication").exists()
    assert "AuthenticationConfig" not in settings
    assert "authentication" not in fastapi_factory
    assert "authentication" not in user_controller
    assert "/v1/users/me" not in user_controller_test


def test_docs_removal_deletes_docs_config_targets_and_links(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(keep_docs=False, delete_wizard=False)

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    assert not (tmp_path / "docs").exists()
    assert "docs" not in _read_toml(tmp_path / "pyproject.toml")["dependency-groups"]
    assert "docs:" not in (tmp_path / "Makefile").read_text()
    assert "## Documentation" not in (tmp_path / "README.md").read_text()


def test_self_delete_removes_wizard_files_and_setup_dependency_group(tmp_path: Path) -> None:
    _create_mini_repo(repo_root=tmp_path)
    answers = _answers(delete_wizard=True)

    build_setup_plan(repo_root=tmp_path, answers=answers).apply(run_commands=False)

    assert not (tmp_path / "management" / "setup_wizard").exists()
    assert not (tmp_path / "tests" / "setup_wizard").exists()
    assert "setup" not in _read_toml(tmp_path / "pyproject.toml")["dependency-groups"]
    assert "setup:" not in (tmp_path / "Makefile").read_text()


def _answers(
    *,
    project_name: str = "Example API",
    package_name: str = "example_api",
    distribution_name: str = "example-api",
    docs_site_url: str | None = None,
    storage_mode: StorageMode = StorageMode.LOCAL,
    database_mode: DatabaseMode = DatabaseMode.DOCKER_POSTGRES,
    redis_mode: RedisMode = RedisMode.DOCKER_REDIS,
    authentication_mode: AuthenticationMode = AuthenticationMode.JWT_REFRESH_SESSION,
    keep_docs: bool = True,
    delete_wizard: bool = True,
    repo_url: str | None = None,
    production_api_origin: str | None = None,
    frontend_origin: str | None = None,
    database_url: str | None = None,
    redis_url: str | None = None,
    enable_logfire: bool = False,
    logfire_token: str | None = None,
    logfire_environment: str = "local",
    postgres_port: int = 5432,
    redis_port: int = 6379,
    minio_api_port: int = 9000,
    minio_console_port: int = 9001,
    s3_endpoint_url: str | None = None,
    s3_public_endpoint_url: str | None = None,
    s3_region_name: str | None = None,
    s3_access_key_id: str | None = None,
    s3_secret_access_key: str | None = None,
) -> SetupAnswers:
    return SetupAnswers(
        project_name=project_name,
        package_name=package_name,
        distribution_name=distribution_name,
        docs_site_url=docs_site_url,
        storage_mode=storage_mode,
        database_mode=database_mode,
        redis_mode=redis_mode,
        authentication_mode=authentication_mode,
        keep_docs=keep_docs,
        delete_wizard=delete_wizard,
        overwrite_env=True,
        repo_url=repo_url,
        production_api_origin=production_api_origin,
        frontend_origin=frontend_origin,
        database_url=database_url,
        redis_url=redis_url,
        enable_logfire=enable_logfire,
        logfire_token=logfire_token,
        logfire_environment=logfire_environment,
        postgres_port=postgres_port,
        redis_port=redis_port,
        minio_api_port=minio_api_port,
        minio_console_port=minio_console_port,
        s3_endpoint_url=s3_endpoint_url,
        s3_public_endpoint_url=s3_public_endpoint_url,
        s3_region_name=s3_region_name,
        s3_access_key_id=s3_access_key_id,
        s3_secret_access_key=s3_secret_access_key,
    )


def _create_mini_repo(*, repo_root: Path) -> None:
    _write(
        repo_root / "src" / "fastdjango" / "core" / "sample.py",
        """
        from fastdjango.foundation.services import BaseService

        MODULE_PATH = "src/fastdjango/core/sample.py"
        SETTINGS_MODULE = "fastdjango.infrastructure.django.settings"


        class SampleService(BaseService):
            pass
        """,
    )
    _write(repo_root / "src" / "fastdjango" / "__init__.py", "")
    _write(
        repo_root / "tests" / "sample_test.py",
        "from fastdjango.core.sample import SampleService\n",
    )
    _create_authentication_files(repo_root=repo_root)
    _write(repo_root / "management" / "setup_wizard" / "__init__.py", "")
    _write(repo_root / "tests" / "setup_wizard" / "test_old.py", "")
    _write(
        repo_root / "README.md",
        "# Fast Django\n\n## Documentation\n\nFull documentation is available at [fastdjango.zayats.dev](https://fastdjango.zayats.dev).\n\n## Tech Stack\n",
    )
    _write(repo_root / "docs" / "mkdocs.yml", _mkdocs_content())
    _write(
        repo_root / "docs" / "en" / "index.md",
        """
        Use src/fastdjango/core/sample.py at https://fastdjango.zayats.dev
        Report bugs at [GitHub Issues](https://github.com/maksimzayats/fastdjango/issues).
        """,
    )
    _write(repo_root / "docs" / "en" / "CNAME", "fastdjango.zayats.dev\n")
    _write(repo_root / ".env.example", "STORAGE_BACKEND=s3\n")
    _write(repo_root / ".env.test.example", "STORAGE_BACKEND=s3\n")
    _write(repo_root / "pyproject.toml", _pyproject_content())
    _write(repo_root / "ruff.toml", _ruff_content())
    _write(repo_root / "prek.toml", _prek_content())
    _write(repo_root / "Makefile", _makefile_content())
    _write(repo_root / "docker" / "docker-compose.yaml", _compose_content())
    _write(repo_root / "docker" / "docker-compose.local.yaml", _compose_overlay_content())
    _write(repo_root / "docker" / "docker-compose.test.yaml", _compose_overlay_content())


def _create_authentication_files(*, repo_root: Path) -> None:
    _write(
        repo_root / "src" / "fastdjango" / "infrastructure" / "django" / "settings.py",
        """
        INSTALLED_APPS = [
            "fastdjango.core.authentication.apps.AuthenticationConfig",
            "fastdjango.core.user.apps.UserConfig",
        ]
        """,
    )
    _write(
        repo_root / "src" / "fastdjango" / "core" / "user" / "models.py",
        """
        from __future__ import annotations

        from typing import TYPE_CHECKING

        from django.contrib.auth.models import AbstractUser
        from django.db import models

        if TYPE_CHECKING:
            from fastdjango.core.authentication.models import RefreshSession


        class User(AbstractUser):
            refresh_sessions: "models.Manager[RefreshSession]"  # noqa: UP037

            email = models.EmailField(verbose_name="email address", unique=True)

            def __str__(self) -> str:
                return f"User(id={self.pk}, username={self.username})"
        """,
    )
    _write(
        repo_root
        / "src"
        / "fastdjango"
        / "core"
        / "user"
        / "delivery"
        / "fastapi"
        / "controllers.py",
        """
        from dataclasses import dataclass

        from diwire import Injected
        from fastapi import APIRouter, Depends

        from fastdjango.core.authentication.delivery.fastapi.auth import (
            AuthenticatedRequest,
            JWTAuthFactory,
        )
        from fastdjango.core.user.delivery.fastapi.schemas import UserSchema
        from fastdjango.foundation.delivery.controllers import BaseAsyncController


        @dataclass(kw_only=True)
        class UserController(BaseAsyncController):
            _jwt_auth_factory: Injected[JWTAuthFactory]

            def register(self, registry: APIRouter) -> None:
                registry.add_api_route(
                    path="/v1/users/me",
                    endpoint=self.get_current_user,
                    methods=["GET"],
                    dependencies=[Depends(self._jwt_auth_factory())],
                    response_model=UserSchema,
                )

            async def get_current_user(self, request: AuthenticatedRequest) -> UserSchema:
                return UserSchema.model_validate(request.state.user, from_attributes=True)
        """,
    )
    _write(
        repo_root / "src" / "fastdjango" / "entrypoints" / "fastapi" / "factories.py",
        """
        from dataclasses import dataclass

        from diwire import Injected
        from fastapi import APIRouter, FastAPI

        from fastdjango.core.authentication.delivery.fastapi.controllers import (
            AuthenticationTokenController,
        )
        from fastdjango.core.user.delivery.fastapi.controllers import UserController
        from fastdjango.foundation.factories import BaseFactory


        @dataclass(kw_only=True)
        class FastAPIFactory(BaseFactory):
            _authentication_token_controller: Injected[AuthenticationTokenController]
            _user_controller: Injected[UserController]

            def __call__(self) -> FastAPI:
                app = FastAPI()
                auth_router = APIRouter(tags=["authentication"])
                self._authentication_token_controller.register(auth_router)
                app.include_router(auth_router)
                user_router = APIRouter(tags=["user"])
                self._user_controller.register(user_router)
                app.include_router(user_router)
                return app
        """,
    )
    _write_authentication_domain_files(repo_root=repo_root)
    _write_authentication_test_files(repo_root=repo_root)


def _write_authentication_domain_files(*, repo_root: Path) -> None:
    files = {
        "apps.py": 'from django.apps import AppConfig\n\n\nclass AuthenticationConfig(AppConfig):\n    name = "fastdjango.core.authentication"\n',
        "dtos.py": "from fastdjango.foundation.dtos import BaseDTO\n\n\nclass TokenDTO(BaseDTO):\n    access_token: str\n",
        "exceptions.py": "class AuthenticationError(Exception):\n    pass\n",
        "models.py": 'from django.db import models\n\n\nclass RefreshSession(models.Model):\n    token = models.CharField(verbose_name="token", max_length=255)\n',
        "use_cases.py": "from fastdjango.foundation.use_cases import BaseUseCase\n\n\nclass AuthenticationUseCase(BaseUseCase):\n    pass\n",
        "delivery/django/admin.py": "from django.contrib import admin\n\nfrom fastdjango.core.authentication.models import RefreshSession\n\nadmin.site.register(RefreshSession)\n",
        "delivery/fastapi/auth.py": "from fastdjango.core.authentication.services.jwt import JWTService\n\n\nclass JWTAuthFactory:\n    pass\n",
        "delivery/fastapi/controllers.py": "class AuthenticationTokenController:\n    pass\n",
        "delivery/fastapi/schemas.py": "class TokenRequestSchema:\n    pass\n",
        "delivery/fastapi/throttling.py": "class UserThrottlerFactory:\n    pass\n",
        "migrations/__init__.py": "",
        "migrations/0001_initial.py": "# refresh session migration\n",
        "services/__init__.py": "",
        "services/jwt.py": "class JWTService:\n    pass\n",
        "services/refresh_session.py": "class RefreshSessionService:\n    pass\n",
    }
    for relative_path, content in files.items():
        _write(
            repo_root / "src" / "fastdjango" / "core" / "authentication" / relative_path,
            content,
        )


def _write_authentication_test_files(*, repo_root: Path) -> None:
    _write(
        repo_root / "tests" / "integration" / "conftest.py",
        """
        import pytest


        @pytest.fixture(scope="function")
        def container(monkeypatch: pytest.MonkeyPatch) -> object:
            monkeypatch.setenv("AUTHENTICATION_MODE", "jwt-refresh-session")
            monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
            return object()
        """,
    )
    _write(
        repo_root / "tests" / "integration" / "factories.py",
        """
        from fastdjango.core.authentication.services.jwt import JWTService


        class TestClientFactory:
            def __call__(self, *, auth_for_user: object | None = None) -> object:
                return JWTService()
        """,
    )
    _write(
        repo_root
        / "tests"
        / "integration"
        / "core"
        / "authentication"
        / "delivery"
        / "fastapi"
        / "test_controllers.py",
        "def test_token_controller() -> None:\n    assert True\n",
    )
    _write(
        repo_root
        / "tests"
        / "integration"
        / "core"
        / "user"
        / "delivery"
        / "fastapi"
        / "test_controllers.py",
        """
        def test_get_current_user(test_client_factory: object, user: object) -> None:
            test_client_factory(auth_for_user=user)
            assert "/v1/users/me"
        """,
    )
    _write(
        repo_root / "tests" / "unit" / "core" / "authentication" / "services" / "test_jwt.py",
        "def test_jwt_service() -> None:\n    assert True\n",
    )
    _write(
        repo_root
        / "tests"
        / "unit"
        / "core"
        / "authentication"
        / "services"
        / "test_refresh_session.py",
        "def test_refresh_session_service() -> None:\n    assert True\n",
    )
    _write(
        repo_root / "tests" / "unit" / "core" / "authentication" / "test_use_cases.py",
        "def test_authentication_use_case() -> None:\n    assert True\n",
    )


def _pyproject_content() -> str:
    return textwrap.dedent(
        """
        [project]
        name = "fastdjango"
        version = "0.1.0"

        [dependency-groups]
        dev = ["pytest"]
        docs = ["mkdocs"]
        setup = ["questionary"]

        [tool.mypy]

        [[tool.mypy.overrides]]
        module = "fastdjango.*.migrations.*"
        disable_error_code = ["no-untyped-def"]

        [tool.django-stubs]
        django_settings_module = "fastdjango.infrastructure.django.settings"

        [tool.coverage.run]
        omit = [
            "src/fastdjango/manage.py",
            "src/fastdjango/infrastructure/django/settings.py",
        ]
        """,
    ).lstrip()


def _ruff_content() -> str:
    return textwrap.dedent(
        """
        src = ["src", "tests"]

        [lint]

        [lint.isort]
        known-first-party = ["fastdjango"]
        """,
    ).lstrip()


def _prek_content() -> str:
    return textwrap.dedent(
        """
        [[repos]]
        repo = "local"

        [[repos.hooks]]
        id = "ruff-check"
        name = "ruff check"
        entry = "uv run ruff check ."
        files = "^(src|tests)/.*\\\\.py$"
        pass_filenames = false

        [[repos.hooks]]
        id = "mypy"
        name = "mypy"
        entry = "uv run --env-file .env.test.example mypy src/ tests/"
        files = "^(src|tests)/.*\\\\.py$"
        pass_filenames = false
        """,
    ).lstrip()


def _makefile_content() -> str:
    return textwrap.dedent(
        """
        migrate:
        \tuv run src/fastdjango/manage.py migrate

        setup:
        \tuv run --group setup python -m management.setup_wizard $(ARGS)

        docs:
        \tuv run mkdocs serve --livereload -f docs/mkdocs.yml

        docs-build:
        \tuv run mkdocs build -f docs/mkdocs.yml

        .PHONY: migrate setup docs docs-build
        """,
    ).lstrip()


def _compose_content() -> str:
    return textwrap.dedent(
        """
        x-common:
          environment:
            DATABASE_URL: "postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@pgbouncer:5432/${POSTGRES_DB}"
            AWS_S3_ENDPOINT_URL: "http://minio:9000"
            REDIS_URL: "redis://default:${REDIS_PASSWORD}@redis:6379/0"

        services:
          api:
            command:
              - fastdjango.entrypoints.fastapi.app:app
            depends_on:
              pgbouncer:
                condition: service_healthy
          migrations:
            command: python src/fastdjango/manage.py migrate --noinput
            depends_on:
              pgbouncer:
                condition: service_healthy
          collectstatic:
            command: python src/fastdjango/manage.py collectstatic --noinput
            depends_on:
              pgbouncer:
                condition: service_healthy
              minio-create-buckets:
                condition: service_completed_successfully
          celery-worker:
            command:
              - celery
              - --app=fastdjango.entrypoints.celery.app
              - worker
            depends_on:
              redis:
                condition: service_healthy
              pgbouncer:
                condition: service_healthy
          celery-beat:
            command:
              - celery
              - --app=fastdjango.entrypoints.celery.app
              - beat
            depends_on:
              redis:
                condition: service_healthy
              pgbouncer:
                condition: service_healthy
          postgres:
            image: postgres:18-alpine
          pgbouncer:
            image: edoburu/pgbouncer:latest
          redis:
            image: redis:latest
          minio:
            image: minio/minio:latest
          minio-create-buckets:
            image: minio/mc

        volumes:
          postgres_data:
            driver: local
          redis_data:
            driver: local
          minio_data:
            driver: local
        """,
    ).lstrip()


def _compose_overlay_content() -> str:
    return textwrap.dedent(
        """
        services:
          postgres:
            ports:
              - "5432:5432"
          redis:
            ports:
              - "6379:6379"
          minio:
            ports:
              - "9000:9000"
              - "9001:9001"
        """,
    ).lstrip()


def _mkdocs_content() -> str:
    return textwrap.dedent(
        """
        site_name: Fast Django
        site_url: https://fastdjango.zayats.dev
        docs_dir: en
        """,
    ).lstrip()


def _assert_markers_in_order(*, content: str, markers: tuple[str, ...]) -> None:
    previous_position = -1
    for marker in markers:
        marker_position = content.find(marker)
        assert marker_position > previous_position
        previous_position = marker_position


def _assert_python_files_parse(*, root: Path) -> None:
    for path in root.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())


def _env_values(*, content: str) -> dict[str, str]:
    return {
        key: value
        for line in content.splitlines()
        if line and not line.startswith("#")
        for key, value in (line.split("=", maxsplit=1),)
    }


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def _read_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))
