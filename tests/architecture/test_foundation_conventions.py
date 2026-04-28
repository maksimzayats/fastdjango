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
    "BaseCeleryTaskController": "Controller",
    "BaseCelerySchema": "Schema",
    "BaseConfigurator": "Configurator",
    "BaseDTO": "DTO",
    "BaseFactory": "Factory",
    "BaseFastAPISchema": "Schema",
    "BaseService": "Service",
    "BaseSettings": "Settings",
    "BaseTasksRegistry": "Registry",
    "BaseThrottler": "Throttler",
    "BaseUseCase": "UseCase",
}

INJECTABLE_BASES = {
    "BaseAsyncController",
    "BaseCeleryTaskController",
    "BaseConfigurator",
    "BaseFactory",
    "BaseService",
    "BaseTasksRegistry",
    "BaseThrottler",
    "BaseUseCase",
}

SERVICE_AND_USE_CASE_BASES = {
    "BaseService",
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


def test_services_and_use_cases_use_keyword_only_method_arguments() -> None:
    violations = [
        f"{module.relative_path}:{method_node.lineno} {class_node.name}.{method_node.name}"
        for module in iter_source_modules()
        for class_node in iter_class_definitions(module)
        if has_base(class_node, SERVICE_AND_USE_CASE_BASES)
        if not class_node.name.startswith("Base")
        for method_node in class_node.body
        if isinstance(method_node, ast.FunctionDef | ast.AsyncFunctionDef)
        if _has_custom_positional_arguments(method_node)
    ]

    assert violations == [], (
        "Service and use-case methods must make custom arguments keyword-only. "
        "Add `*` after self/cls, for example `def create(self, *, data: DTO)`, "
        "and avoid positional `*args`."
    )


def _has_custom_positional_arguments(
    method_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    if method_node.args.vararg is not None:
        return True

    positional_arguments = [
        argument.arg for argument in [*method_node.args.posonlyargs, *method_node.args.args]
    ]

    if positional_arguments and positional_arguments[0] in {"self", "cls"}:
        positional_arguments = positional_arguments[1:]

    return bool(positional_arguments)
