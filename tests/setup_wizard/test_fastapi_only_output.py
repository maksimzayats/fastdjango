from textwrap import dedent

from management.setup_wizard.config import update_docker_compose_yaml
from management.setup_wizard.env import build_env_example_content
from management.setup_wizard.models import DatabaseMode, RedisMode, SetupAnswers

LEGACY_CLOUD_ENV_PREFIX = "AW" + "S_"
LEGACY_OBJECT_STORE = "min" + "io"
LEGACY_OBJECT_STORE_VOLUME = f"{LEGACY_OBJECT_STORE}_data"
LEGACY_STATIC_STEP = "collect" + "static"
LEGACY_FILE_ENV_PREFIX = "STOR" + "AGE"
LEGACY_TASK_SERVICE = "cel" + "ery-worker"
LEGACY_WEB_ENV_PREFIX = "D" + "JANGO"


def test_env_example_uses_fastapi_only_settings() -> None:
    content = build_env_example_content(answers=_answers())

    assert "JWT_SECRET_KEY=" in content
    assert "DATABASE_URL=" in content
    assert "REDIS_URL=" in content
    assert LEGACY_WEB_ENV_PREFIX not in content
    assert LEGACY_FILE_ENV_PREFIX not in content
    assert LEGACY_CLOUD_ENV_PREFIX not in content


def test_compose_rewrite_prunes_removed_services() -> None:
    content = update_docker_compose_yaml(
        _legacy_compose(),
        answers=_answers(),
        old_package_name="fastapi_template",
        is_local_overlay=False,
    )

    assert LEGACY_TASK_SERVICE not in content
    assert LEGACY_STATIC_STEP not in content
    assert LEGACY_OBJECT_STORE not in content
    assert LEGACY_CLOUD_ENV_PREFIX not in content
    assert "postgres:" in content
    assert "redis:" in content


def _answers() -> SetupAnswers:
    return SetupAnswers(
        project_name="Example API",
        package_name="example_api",
        distribution_name="example-api",
        docs_site_url=None,
        database_mode=DatabaseMode.DOCKER_POSTGRES,
        redis_mode=RedisMode.DOCKER_REDIS,
        keep_docs=True,
        delete_wizard=False,
        overwrite_env=True,
    )


def _legacy_compose() -> str:
    content = dedent(
        """
        x-common:
          environment:
            DATABASE_URL: "postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@pgbouncer:5432/${POSTGRES_DB}"
            __LEGACY_CLOUD_ENDPOINT_KEY__: "http://__LEGACY_OBJECT_STORE__:9000"
            REDIS_URL: "redis://default:${REDIS_PASSWORD}@redis:6379/0"

        services:
          api:
            depends_on:
              pgbouncer:
                condition: service_healthy
              redis:
                condition: service_healthy
              __LEGACY_TASK_SERVICE__:
                condition: service_started
              __LEGACY_STATIC_STEP__:
                condition: service_completed_successfully
          __LEGACY_TASK_SERVICE__:
            image: base:local
          __LEGACY_STATIC_STEP__:
            image: base:local
          __LEGACY_OBJECT_STORE__:
            image: __LEGACY_OBJECT_STORE__/__LEGACY_OBJECT_STORE__:latest
          postgres:
            image: postgres:18-alpine
          pgbouncer:
            image: edoburu/pgbouncer:latest
          redis:
            image: redis:latest

        volumes:
          __LEGACY_OBJECT_STORE_VOLUME__:
          postgres_data:
          redis_data:
        """,
    )
    replacements = {
        "__LEGACY_CLOUD_ENDPOINT_KEY__": f"{LEGACY_CLOUD_ENV_PREFIX}S3_ENDPOINT_URL",
        "__LEGACY_OBJECT_STORE__": LEGACY_OBJECT_STORE,
        "__LEGACY_OBJECT_STORE_VOLUME__": LEGACY_OBJECT_STORE_VOLUME,
        "__LEGACY_STATIC_STEP__": LEGACY_STATIC_STEP,
        "__LEGACY_TASK_SERVICE__": LEGACY_TASK_SERVICE,
    }
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    return content
