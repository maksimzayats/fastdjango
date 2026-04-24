import os

import django
from django.apps import apps
from dotenv import find_dotenv, load_dotenv


def configure_django_for_tests() -> None:
    load_dotenv()

    test_env_path = find_dotenv(".env.test", raise_error_if_not_found=False)
    if test_env_path:
        load_dotenv(test_env_path, override=True)
    else:
        test_env_example_path = find_dotenv(".env.test.example", raise_error_if_not_found=False)
        if test_env_example_path:
            load_dotenv(test_env_example_path, override=True)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fastdjango.infrastructure.django.settings")

    if not apps.ready:
        django.setup()


configure_django_for_tests()


def pytest_configure() -> None:
    configure_django_for_tests()
