import os

import django
from dotenv import find_dotenv, load_dotenv


def pytest_configure() -> None:
    load_dotenv()

    test_env_path = find_dotenv(".env.test", raise_error_if_not_found=False)
    if test_env_path:
        load_dotenv(test_env_path, override=True)
    else:
        test_env_example_path = find_dotenv(".env.test.example", raise_error_if_not_found=False)
        if test_env_example_path:
            load_dotenv(test_env_example_path, override=True)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fastdjango.infrastructure.django.settings")

    django.setup()
