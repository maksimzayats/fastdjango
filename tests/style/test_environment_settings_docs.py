import ast
from typing import get_args, get_origin

from pydantic_settings import BaseSettings

from fastapi_template.core.authentication.services.jwt import JWTServiceSettings
from fastapi_template.core.authentication.services.refresh_session import (
    RefreshSessionServiceSettings,
)
from fastapi_template.core.shared.delivery.fastapi.request import RequestInfoServiceSettings
from fastapi_template.core.user.services.password import PasswordServiceSettings
from fastapi_template.entrypoints.fastapi.settings.cors import CORSSettings
from fastapi_template.entrypoints.fastapi.settings.fastapi import FastAPISettings
from fastapi_template.infrastructure.logfire.configurator import LogfireSettings
from fastapi_template.infrastructure.logfire.instrumentor import InstrumentorSettings
from fastapi_template.infrastructure.logging.configurator import LoggingSettings
from fastapi_template.infrastructure.settings import ApplicationSettings
from fastapi_template.infrastructure.sqlalchemy.session import DatabaseSettings
from fastapi_template.infrastructure.throttled.settings import ThrottledRedisSettings
from tests.architecture._source import REPO_ROOT, iter_source_modules, name_for_expression

ENVIRONMENT_REFERENCE = REPO_ROOT / "docs" / "en" / "reference" / "environment-variables.md"
EXAMPLE_FILES = (
    REPO_ROOT / ".env.example",
    REPO_ROOT / ".env.test.example",
)
SETTINGS_CLASSES = (
    ApplicationSettings,
    FastAPISettings,
    CORSSettings,
    JWTServiceSettings,
    RefreshSessionServiceSettings,
    PasswordServiceSettings,
    RequestInfoServiceSettings,
    LogfireSettings,
    InstrumentorSettings,
    LoggingSettings,
    DatabaseSettings,
    ThrottledRedisSettings,
)


def test_settings_registry_covers_all_runtime_base_settings_classes() -> None:
    registered_names = sorted(settings_class.__name__ for settings_class in SETTINGS_CLASSES)
    source_names = sorted(_base_settings_class_names_in_source())

    assert registered_names == source_names


def test_environment_reference_documents_all_runtime_settings() -> None:
    reference_text = ENVIRONMENT_REFERENCE.read_text(encoding="utf-8")
    missing_names = sorted(
        name for name in _settings_environment_names() if f"`{name}`" not in reference_text
    )

    assert missing_names == []


def test_environment_examples_cover_required_settings() -> None:
    example_text = "\n".join(
        path.read_text(encoding="utf-8") for path in EXAMPLE_FILES if path.exists()
    )
    missing_names = sorted(
        name for name in _required_environment_names() if f"{name}=" not in example_text
    )

    assert missing_names == []


def _settings_environment_names() -> set[str]:
    return {
        environment_name
        for settings_class in SETTINGS_CLASSES
        for environment_name in _environment_names_for_settings_class(settings_class)
    }


def _required_environment_names() -> set[str]:
    return {
        environment_name
        for settings_class in SETTINGS_CLASSES
        for environment_name, is_required in _environment_fields(settings_class)
        if is_required
    }


def _environment_names_for_settings_class(
    settings_class: type[BaseSettings],
) -> set[str]:
    return {
        environment_name for environment_name, _is_required in _environment_fields(settings_class)
    }


def _environment_fields(
    settings_class: type[BaseSettings],
) -> set[tuple[str, bool]]:
    prefix = str(settings_class.model_config.get("env_prefix") or "")
    return {
        (f"{prefix}{field_name}".upper(), field_info.is_required())
        for field_name, field_info in settings_class.model_fields.items()
        if not _is_nested_settings(annotation=field_info.annotation)
    }


def _is_nested_settings(*, annotation: object) -> bool:
    if isinstance(annotation, type) and issubclass(annotation, BaseSettings):
        return True

    origin = get_origin(annotation)
    if origin is None:
        return False

    return any(_is_nested_settings(annotation=argument) for argument in get_args(annotation))


def _base_settings_class_names_in_source() -> set[str]:
    names: set[str] = set()
    for module in iter_source_modules():
        for node in ast.walk(module.tree):
            if isinstance(node, ast.ClassDef) and _extends_base_settings(class_node=node):
                names.add(node.name)

    return names


def _extends_base_settings(*, class_node: ast.ClassDef) -> bool:
    return any(name_for_expression(base) == "BaseSettings" for base in class_node.bases)
