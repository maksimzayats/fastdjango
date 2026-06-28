import os

import pytest
from dotenv import find_dotenv, load_dotenv


def configure_environment_for_tests() -> None:
    load_dotenv()

    test_env_path = find_dotenv(".env.test", raise_error_if_not_found=False)
    if test_env_path:
        load_dotenv(test_env_path, override=True)
    else:
        test_env_example_path = find_dotenv(".env.test.example", raise_error_if_not_found=False)
        if test_env_example_path:
            load_dotenv(test_env_example_path, override=True)

    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("LOGFIRE_ENABLED", "false")
    os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-with-at-least-32-bytes")


configure_environment_for_tests()


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"
