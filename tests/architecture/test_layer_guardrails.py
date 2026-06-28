import ast

from tests.architecture._source import (
    SOURCE_ROOT,
    SourceModule,
    is_injected_annotation,
    iter_imports,
    iter_source_modules,
    name_for_expression,
)

FORBIDDEN_RUNTIME_IMPORT_PREFIXES = ("cel" + "ery", "djan" + "go")
SQLALCHEMY_ALLOWED_SOURCE_PARTS = {
    ("core", "authentication", "models.py"),
    ("core", "authentication", "repositories.py"),
    ("core", "database.py"),
    ("core", "health", "repositories.py"),
    ("core", "user", "models.py"),
    ("core", "user", "repositories.py"),
    ("infrastructure", "database", "session.py"),
    ("infrastructure", "database", "unit_of_work.py"),
}
DATABASE_REPOSITORY_SOURCE_PARTS = {
    ("core", "authentication", "repositories.py"),
    ("core", "health", "repositories.py"),
    ("core", "user", "repositories.py"),
}
DATABASE_INFRASTRUCTURE_MODULES = {
    "__init__.py",
    "session.py",
    "unit_of_work.py",
}
DATABASE_DOMAIN_MODEL_SOURCE_PARTS = (
    ("core", "authentication", "models.py"),
    ("core", "user", "models.py"),
)
FRAMEWORK_IMPORT_PREFIXES = ("fastapi", "starlette")
DATABASE_QUERY_FUNCTION_NAMES = {"delete", "insert", "select", "text", "update"}


def test_runtime_code_does_not_import_removed_frameworks() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        for import_reference in iter_imports(module)
        if not import_reference.is_type_checking
        if import_reference.module_name.startswith(FORBIDDEN_RUNTIME_IMPORT_PREFIXES)
    ]

    assert violations == [], "Runtime source must not import removed frameworks."


def test_sqlalchemy_imports_stay_in_application_database_boundaries() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if module.source_parts not in SQLALCHEMY_ALLOWED_SOURCE_PARTS
        for import_reference in iter_imports(module)
        if not import_reference.is_type_checking
        if import_reference.module_name.startswith("sqlalchemy")
    ]

    assert violations == [], (
        "SQLAlchemy imports are allowed only in core models/repositories and "
        "infrastructure database session/UoW wiring."
    )


def test_database_infrastructure_keeps_only_session_and_unit_of_work_wiring() -> None:
    database_infrastructure_modules = {
        path.name for path in (SOURCE_ROOT / "infrastructure" / "database").glob("*.py")
    }

    assert database_infrastructure_modules <= DATABASE_INFRASTRUCTURE_MODULES


def test_sqlalchemy_domain_models_live_in_core_domain_modules() -> None:
    model_modules = {
        module.source_parts
        for module in iter_source_modules()
        if any(
            node.name.endswith("Model")
            for node in ast.walk(module.tree)
            if isinstance(node, ast.ClassDef)
        )
    }

    assert model_modules == set(DATABASE_DOMAIN_MODEL_SOURCE_PARTS)


def test_database_query_execution_stays_in_repositories() -> None:
    violations = [
        f"{module.relative_path}:{node.lineno} calls {call_name}"
        for module in iter_source_modules()
        if module.source_parts not in DATABASE_REPOSITORY_SOURCE_PARTS
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
        if (call_name := _database_query_call_name(node)) is not None
    ]

    assert violations == [], "Runtime database queries must go through core repositories."


def test_core_domain_internals_do_not_import_delivery_or_composition_layers() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_core_internal_module(module)
        for import_reference in iter_imports(module)
        if not import_reference.is_type_checking
        if _is_forbidden_core_internal_import(import_reference.module_name)
    ]

    assert violations == [], (
        "Core domain internals must not import delivery, infrastructure, entrypoints, or IoC."
    )


def test_framework_imports_stay_in_delivery_entrypoints_or_infrastructure() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if not _is_framework_boundary_module(module)
        for import_reference in iter_imports(module)
        if not import_reference.is_type_checking
        if _is_framework_import(import_reference.module_name)
    ]

    assert violations == [], (
        "FastAPI and Starlette imports must stay in delivery, entrypoint, or infrastructure modules."
    )


def test_http_route_paths_are_full_api_v1_paths() -> None:
    violations = [
        f"{module.relative_path}:{node.lineno} path={path!r}"
        for module in iter_source_modules()
        if _is_fastapi_delivery_module(module)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
        for path in _route_path_values(node)
        if not path.startswith("/api/v1/")
    ]

    assert violations == [], "Public FastAPI route paths must be full /api/v1/... paths."


def test_container_access_stays_in_composition_roots() -> None:
    violations = [
        f"{module.relative_path}:{node.lineno} calls get_container()"
        for module in iter_source_modules()
        if not _can_access_container(module)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
        if isinstance(node.func, ast.Name)
        if node.func.id == "get_container"
    ]
    violations.extend(
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if not _can_access_container(module)
        for import_reference in iter_imports(module)
        if not import_reference.is_type_checking
        if import_reference.module_name.startswith("fastapi_template.ioc")
    )

    assert violations == [], "Only composition roots may access the IoC container."


def test_services_and_use_cases_depend_on_unit_of_work_for_persistence() -> None:
    violations = [
        f"{module.relative_path}:{node.lineno} injects {dependency_name}"
        for module in iter_source_modules()
        if _is_service_or_use_case_module(module)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.AnnAssign)
        if is_injected_annotation(node.annotation)
        if (dependency_name := _injected_dependency_name(node.annotation)) is not None
        if dependency_name.endswith("Repository")
    ]

    assert violations == [], "Use cases and services must inject UnitOfWork, not repositories."


def _format_import_violation(
    module: SourceModule,
    module_name: str,
    line_number: int,
) -> str:
    return f"{module.relative_path}:{line_number} imports {module_name}"


def _is_core_internal_module(module: SourceModule) -> bool:
    return (
        module.source_parts[0] == "core"
        and "delivery" not in module.source_parts
        and module.path.name != "__init__.py"
    )


def _is_forbidden_core_internal_import(module_name: str) -> bool:
    if module_name.startswith(
        (
            "fastapi_template.entrypoints",
            "fastapi_template.infrastructure",
            "fastapi_template.ioc",
        ),
    ):
        return True

    return module_name.startswith("fastapi_template.core.") and ".delivery." in module_name


def _is_framework_boundary_module(module: SourceModule) -> bool:
    return "delivery" in module.source_parts or module.source_parts[0] in {
        "entrypoints",
        "infrastructure",
    }


def _is_framework_import(module_name: str) -> bool:
    return any(
        module_name == prefix or module_name.startswith(f"{prefix}.")
        for prefix in FRAMEWORK_IMPORT_PREFIXES
    )


def _is_fastapi_delivery_module(module: SourceModule) -> bool:
    return "delivery" in module.source_parts and "fastapi" in module.source_parts


def _route_path_values(node: ast.Call) -> list[str]:
    route_function_names = {"add_api_route", "add_api_websocket_route"}
    if not isinstance(node.func, ast.Attribute) or node.func.attr not in route_function_names:
        return []

    return [
        keyword.value.value
        for keyword in node.keywords
        if (
            keyword.arg == "path"
            and isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, str)
        )
    ]


def _can_access_container(module: SourceModule) -> bool:
    return module.source_parts[0] in {"entrypoints", "ioc"}


def _database_query_call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name) and node.func.id in DATABASE_QUERY_FUNCTION_NAMES:
        return node.func.id

    if not isinstance(node.func, ast.Attribute):
        return None

    if node.func.attr == "execute" and name_for_expression(node.func.value) in {
        "_connection",
        "_session",
        "connection",
        "session",
    }:
        return "execute"

    if node.func.attr == "get" and name_for_expression(node.func.value) == "_session":
        return "session.get"

    return None


def _is_service_or_use_case_module(module: SourceModule) -> bool:
    return (
        module.source_parts[0] == "core"
        and "delivery" not in module.source_parts
        and (module.path.name == "use_cases.py" or "services" in module.source_parts)
    )


def _injected_dependency_name(annotation: ast.expr) -> str | None:
    if not isinstance(annotation, ast.Subscript):
        return None

    return name_for_expression(annotation.slice)
