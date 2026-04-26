import ast

from tests.architecture._source import (
    SourceModule,
    base_names,
    has_base,
    iter_class_definitions,
    iter_imports,
    iter_source_modules,
)

DELIVERY_SCHEMA_BASES = {
    "celery": "BaseCelerySchema",
    "fastapi": "BaseFastAPISchema",
}
DTO_FORBIDDEN_IMPORT_PREFIXES = (
    "django",
    "fastapi",
    "starlette",
    "celery",
    "fastdjango.infrastructure",
)


def test_dtos_live_in_dto_modules_and_inherit_base_dto() -> None:
    violations = [
        violation
        for module in iter_source_modules()
        for class_node in iter_class_definitions(module)
        for violation in _dto_violations(module=module, class_node=class_node)
    ]

    assert violations == [], "DTO classes must live in dtos.py, inherit BaseDTO, and end with DTO."


def test_delivery_schemas_live_in_schema_modules_and_inherit_delivery_schema_base() -> None:
    violations = [
        violation
        for module in iter_source_modules()
        for class_node in iter_class_definitions(module)
        for violation in _delivery_schema_violations(module=module, class_node=class_node)
    ]

    assert violations == [], (
        "Delivery schema classes must live in delivery schema modules, inherit the matching "
        "delivery schema base, and end with Schema."
    )


def test_non_delivery_code_does_not_import_delivery_schemas() -> None:
    violations = [
        f"{module.relative_path}:{import_reference.line_number} imports {import_reference.module_name}"
        for module in iter_source_modules()
        if "delivery" not in module.source_parts
        for import_reference in iter_imports(module)
        if not import_reference.is_type_checking
        if _is_delivery_schema_module(import_reference.module_name)
    ]

    assert violations == [], "Delivery schemas must not leak into non-delivery modules."


def test_dtos_do_not_import_framework_or_infrastructure_modules() -> None:
    violations = [
        f"{module.relative_path}:{import_reference.line_number} imports {import_reference.module_name}"
        for module in iter_source_modules()
        if _is_dto_module(module)
        for import_reference in iter_imports(module)
        if _is_forbidden_dto_import(import_reference.module_name)
    ]

    assert violations == [], (
        "DTOs must stay framework-neutral and must not import Django, FastAPI, "
        "Starlette, Celery, or infrastructure modules."
    )


def test_delivery_schemas_are_thin_data_shapes() -> None:
    violations = [
        f"{module.relative_path}:{statement.lineno} {class_node.name} contains {statement_name}"
        for module in iter_source_modules()
        if _delivery_schema_framework(module) is not None
        for class_node in iter_class_definitions(module)
        for statement in class_node.body
        if (statement_name := _schema_behavior_statement_name(statement)) is not None
    ]

    assert violations == [], (
        "Delivery schemas must be thin data shapes: annotated fields only, "
        "with no methods, validators, config, constants, or behavior."
    )


def _dto_violations(*, module: SourceModule, class_node: ast.ClassDef) -> list[str]:
    violations: list[str] = []
    is_dto_file = _is_dto_module(module)
    is_dto_class = has_base(class_node, {"BaseDTO"})

    if is_dto_file and not is_dto_class:
        violations.append(f"{module.relative_path}:{class_node.lineno} {class_node.name}")

    if is_dto_class and not is_dto_file:
        violations.append(f"{module.relative_path}:{class_node.lineno} {class_node.name}")

    if is_dto_class and not class_node.name.endswith("DTO"):
        violations.append(f"{module.relative_path}:{class_node.lineno} {class_node.name}")

    return violations


def _delivery_schema_violations(
    *,
    module: SourceModule,
    class_node: ast.ClassDef,
) -> list[str]:
    violations: list[str] = []
    framework_name = _delivery_schema_framework(module)
    schema_base_names = set(DELIVERY_SCHEMA_BASES.values())
    class_base_names = base_names(class_node)
    is_delivery_schema_class = not class_base_names.isdisjoint(schema_base_names)

    if framework_name is not None:
        expected_base = DELIVERY_SCHEMA_BASES[framework_name]
        if not has_base(class_node, {expected_base}):
            violations.append(f"{module.relative_path}:{class_node.lineno} {class_node.name}")

    if is_delivery_schema_class and framework_name is None:
        violations.append(f"{module.relative_path}:{class_node.lineno} {class_node.name}")

    if is_delivery_schema_class and not class_node.name.endswith("Schema"):
        violations.append(f"{module.relative_path}:{class_node.lineno} {class_node.name}")

    return violations


def _delivery_schema_framework(module: SourceModule) -> str | None:
    if module.source_parts[0] != "core":
        return None

    if module.path.name != "schemas.py":
        return None

    parts = module.source_parts
    for framework_name in DELIVERY_SCHEMA_BASES:
        if "delivery" in parts and framework_name in parts:
            return framework_name

    return None


def _is_dto_module(module: SourceModule) -> bool:
    return module.source_parts[0] == "core" and module.path.name == "dtos.py"


def _is_forbidden_dto_import(module_name: str) -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in DTO_FORBIDDEN_IMPORT_PREFIXES
    )


def _is_delivery_schema_module(module_name: str) -> bool:
    parts = module_name.split(".")
    return "delivery" in parts and parts[-1] == "schemas"


def _schema_behavior_statement_name(statement: ast.stmt) -> str | None:
    if isinstance(statement, ast.AnnAssign | ast.Pass):
        return None

    if (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    ):
        return None

    return statement.__class__.__name__
