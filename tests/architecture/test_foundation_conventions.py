import ast

from tests.architecture._source import (
    has_base,
    has_dataclass_kw_only_decorator,
    is_classvar_annotation,
    is_injected_annotation,
    iter_class_definitions,
    iter_source_modules,
)

FOUNDATION_BASE_SUFFIXES = {
    "ApplicationSettings": "Settings",
    "BaseAsyncController": "Controller",
    "BaseCelerySchema": "Schema",
    "BaseConfigurator": "Configurator",
    "BaseController": "Controller",
    "BaseDTO": "DTO",
    "BaseFactory": "Factory",
    "BaseFastAPISchema": "Schema",
    "BaseService": "Service",
    "BaseSettings": "Settings",
    "BaseTasksRegistry": "Registry",
    "BaseThrottler": "Throttler",
    "BaseTransactionController": "Controller",
    "BaseUseCase": "UseCase",
}

INJECTABLE_BASES = {
    "BaseAsyncController",
    "BaseConfigurator",
    "BaseController",
    "BaseFactory",
    "BaseService",
    "BaseTasksRegistry",
    "BaseThrottler",
    "BaseTransactionController",
    "BaseUseCase",
}


def test_foundation_subclasses_use_expected_name_suffixes() -> None:
    violations = [
        (
            f"{module.relative_path}:{class_node.lineno} {class_node.name} "
            f"inherits {base_name} and must end with {expected_suffix}"
        )
        for module in iter_source_modules()
        for class_node in iter_class_definitions(module)
        for base_name, expected_suffix in FOUNDATION_BASE_SUFFIXES.items()
        if has_base(class_node, {base_name})
        if not class_node.name.endswith(expected_suffix)
    ]

    assert violations == [], "Classes inheriting foundation markers must use the matching postfix."


def test_injectable_classes_are_keyword_only_dataclasses() -> None:
    violations = [
        f"{module.relative_path}:{class_node.lineno} {class_node.name}"
        for module in iter_source_modules()
        for class_node in iter_class_definitions(module)
        if has_base(class_node, INJECTABLE_BASES)
        if not class_node.name.startswith("Base")
        if not has_dataclass_kw_only_decorator(class_node)
    ]

    assert violations == [], (
        "Injectable services, use cases, factories, configurators, controllers, "
        "registries, and throttlers must use @dataclass(kw_only=True)."
    )


def test_injectable_dataclass_fields_are_private() -> None:
    violations = [
        f"{module.relative_path}:{field_node.lineno} {class_node.name}.{field_node.target.id}"
        for module in iter_source_modules()
        for class_node in iter_class_definitions(module)
        if has_base(class_node, INJECTABLE_BASES)
        if not class_node.name.startswith("Base")
        for field_node in class_node.body
        if isinstance(field_node, ast.AnnAssign)
        if isinstance(field_node.target, ast.Name)
        if not is_classvar_annotation(field_node.annotation)
        if not field_node.target.id.startswith("_")
    ]

    assert violations == [], "Injectable dataclass fields must be private."


def test_injectable_dataclass_dependencies_use_injected_marker() -> None:
    violations = [
        f"{module.relative_path}:{field_node.lineno} {class_node.name}.{field_node.target.id}"
        for module in iter_source_modules()
        for class_node in iter_class_definitions(module)
        if not class_node.name.startswith("Base")
        if has_dataclass_kw_only_decorator(class_node)
        for field_node in class_node.body
        if isinstance(field_node, ast.AnnAssign)
        if isinstance(field_node.target, ast.Name)
        if field_node.value is None
        if field_node.target.id.startswith("_")
        if not is_classvar_annotation(field_node.annotation)
        if not is_injected_annotation(field_node.annotation)
    ]

    assert violations == [], (
        "Required private dataclass dependencies must be annotated with diwire.Injected."
    )
