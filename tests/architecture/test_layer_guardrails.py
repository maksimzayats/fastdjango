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
SHARED_SQLALCHEMY_SOURCE_PARTS = {
    ("infrastructure", "sqlalchemy", "base.py"),
    ("infrastructure", "sqlalchemy", "metadata.py"),
    ("infrastructure", "sqlalchemy", "session.py"),
    ("infrastructure", "sqlalchemy", "unit_of_work.py"),
}
SHARED_SQLALCHEMY_MODULES = {
    "__init__.py",
    "base.py",
    "metadata.py",
    "session.py",
    "unit_of_work.py",
}
DATABASE_DOMAIN_MODEL_SOURCE_PARTS = {
    (
        "core",
        "authentication",
        "infrastructure",
        "sqlalchemy",
        "models",
        "refresh_session.py",
    ),
    ("core", "user", "infrastructure", "sqlalchemy", "models", "user.py"),
}
FRAMEWORK_IMPORT_PREFIXES = ("fastapi", "starlette")
DATABASE_QUERY_FUNCTION_NAMES = {"delete", "insert", "select", "text", "update"}
REPOSITORY_TRANSACTION_METHODS = {
    "begin",
    "close",
    "commit",
    "rollback",
}
REPOSITORY_SESSION_FACTORY_CALLS = {"async_sessionmaker", "create_async_engine"}
FORBIDDEN_CONTROLLER_IMPORT_PREFIXES = (
    "sqlalchemy",
    "fastapi_template.infrastructure.sqlalchemy.unit_of_work",
)


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
        if not _can_import_sqlalchemy(module)
        for import_reference in iter_imports(module)
        if import_reference.module_name.startswith("sqlalchemy")
    ]

    assert violations == [], (
        "SQLAlchemy imports are allowed only in shared database wiring or local "
        "core SQLAlchemy adapters."
    )


def test_sqlalchemy_infrastructure_keeps_only_shared_wiring() -> None:
    sqlalchemy_infrastructure_modules = {
        path.name for path in (SOURCE_ROOT / "infrastructure" / "sqlalchemy").glob("*.py")
    }

    assert sqlalchemy_infrastructure_modules <= SHARED_SQLALCHEMY_MODULES


def test_local_infrastructure_does_not_use_persistence_nesting() -> None:
    """Ensure local adapters do not reintroduce an extra persistence package."""
    persistence_paths = [
        path.relative_to(SOURCE_ROOT)
        for path in sorted(SOURCE_ROOT.glob("core/*/infrastructure/persistence"))
    ]

    assert persistence_paths == []


def test_sqlalchemy_domain_models_live_in_local_sqlalchemy_adapters() -> None:
    model_modules = {
        module.source_parts
        for module in iter_source_modules()
        if any(
            node.name.endswith("Model")
            for node in ast.walk(module.tree)
            if isinstance(node, ast.ClassDef)
        )
    }

    assert model_modules == DATABASE_DOMAIN_MODEL_SOURCE_PARTS


def test_database_query_execution_stays_in_local_sqlalchemy_repositories() -> None:
    violations = [
        f"{module.relative_path}:{node.lineno} calls {call_name}"
        for module in iter_source_modules()
        if not _is_local_sqlalchemy_repository_module(module)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
        if (call_name := _database_query_call_name(node)) is not None
    ]

    assert violations == [], (
        "Runtime SQLAlchemy query construction and execution must stay in local "
        "SQLAlchemy repository adapters."
    )


def test_repository_ports_do_not_import_sqlalchemy() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_repository_port_module(module)
        for import_reference in iter_imports(module)
        if import_reference.module_name.startswith("sqlalchemy")
    ]

    assert violations == [], "Repository port modules must not import SQLAlchemy."


def test_repositories_do_not_manage_transaction_lifecycle() -> None:
    violations = [
        f"{module.relative_path}:{node.lineno} calls {call_name}"
        for module in iter_source_modules()
        if _is_repository_module(module)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
        if (call_name := _repository_lifecycle_call_name(node)) is not None
    ]

    assert violations == [], (
        "Repositories may flush, but only the UnitOfWork may commit, rollback, close "
        "sessions, begin transactions, or create session factories."
    )


def test_core_domain_internals_do_not_import_delivery_or_infrastructure() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_core_internal_module(module)
        for import_reference in iter_imports(module)
        if _is_forbidden_core_internal_import(import_reference.module_name)
    ]

    assert violations == [], (
        "Inner core modules must not import delivery, local infrastructure, "
        "top-level infrastructure, entrypoints, or IoC."
    )


def test_local_infrastructure_modules_do_not_import_delivery() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_core_local_infrastructure_module(module)
        for import_reference in iter_imports(module)
        if _is_core_delivery_import(import_reference.module_name)
    ]

    assert violations == [], "Local infrastructure adapters must not import delivery modules."


def test_delivery_modules_do_not_import_local_infrastructure() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_core_delivery_module(module)
        for import_reference in iter_imports(module)
        if _is_core_local_infrastructure_import(import_reference.module_name)
    ]

    assert violations == [], "Delivery adapters must not import local infrastructure modules."


def test_controllers_do_not_import_sqlalchemy_or_uow_implementations() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_controller_module(module)
        for import_reference in iter_imports(module)
        if _is_forbidden_controller_import(import_reference.module_name)
    ]

    assert violations == [], (
        "Controllers must not import repositories, UoW implementations, SQLAlchemy, "
        "SQLAlchemy models, or local infrastructure."
    )


def test_services_do_not_open_unit_of_work_scopes() -> None:
    violations = [
        f"{module.relative_path}:{node.lineno} opens self._uow"
        for module in iter_source_modules()
        if _is_service_module(module)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.AsyncWith)
        for item in node.items
        if name_for_expression(item.context_expr) == "_uow"
    ]

    assert violations == [], "Services may receive an active UoW, but must not open UoW scopes."


def test_framework_imports_stay_in_delivery_entrypoints_or_infrastructure() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if not _is_framework_boundary_module(module)
        for import_reference in iter_imports(module)
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
        if import_reference.module_name.startswith("fastapi_template.ioc")
    )

    assert violations == [], "Only composition roots may access the IoC container."


def test_services_and_use_cases_depend_on_unit_of_work_for_database_access() -> None:
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


def test_scoped_import_predicates_catch_package_and_module_imports() -> None:
    assert _is_core_delivery_import("fastapi_template.core.user.delivery")
    assert _is_core_delivery_import("fastapi_template.core.user.delivery.fastapi")
    assert _is_core_local_infrastructure_import("fastapi_template.core.user.infrastructure")
    assert _is_core_local_infrastructure_import(
        "fastapi_template.core.user.infrastructure.sqlalchemy",
    )
    assert _is_forbidden_controller_import("fastapi_template.core.user.repositories")
    assert _is_forbidden_controller_import("fastapi_template.core.user.repositories.user")
    assert _is_forbidden_controller_import(
        "fastapi_template.core.user.infrastructure.sqlalchemy.models.user",
    )


def _format_import_violation(
    module: SourceModule,
    module_name: str,
    line_number: int,
) -> str:
    return f"{module.relative_path}:{line_number} imports {module_name}"


def _can_import_sqlalchemy(module: SourceModule) -> bool:
    return (
        module.source_parts in SHARED_SQLALCHEMY_SOURCE_PARTS
        or _is_local_sqlalchemy_adapter_module(module)
    )


def _is_core_internal_module(module: SourceModule) -> bool:
    return (
        module.source_parts[0] == "core"
        and not _is_core_delivery_module(module)
        and not _is_core_local_infrastructure_module(module)
        and module.path.name != "__init__.py"
    )


def _is_core_local_infrastructure_module(module: SourceModule) -> bool:
    return module.source_parts[0] == "core" and "infrastructure" in module.source_parts


def _is_core_delivery_module(module: SourceModule) -> bool:
    return module.source_parts[0] == "core" and "delivery" in module.source_parts


def _is_local_sqlalchemy_adapter_module(module: SourceModule) -> bool:
    parts = module.source_parts
    return len(parts) >= 5 and parts[0] == "core" and parts[2:4] == ("infrastructure", "sqlalchemy")


def _is_local_sqlalchemy_repository_module(module: SourceModule) -> bool:
    return _is_local_sqlalchemy_adapter_module(module) and "repositories" in module.source_parts


def _is_repository_port_module(module: SourceModule) -> bool:
    return (
        module.source_parts[0] == "core"
        and "repositories" in module.source_parts
        and "infrastructure" not in module.source_parts
    )


def _is_repository_module(module: SourceModule) -> bool:
    return module.source_parts[0] == "core" and "repositories" in module.source_parts


def _is_forbidden_core_internal_import(module_name: str) -> bool:
    if module_name.startswith(
        (
            "fastapi_template.entrypoints",
            "fastapi_template.infrastructure",
            "fastapi_template.ioc",
        ),
    ):
        return True

    return _is_core_delivery_import(module_name) or _is_core_local_infrastructure_import(
        module_name,
    )


def _is_core_delivery_import(module_name: str) -> bool:
    return _has_core_package_part(module_name=module_name, package_part="delivery")


def _is_core_local_infrastructure_import(module_name: str) -> bool:
    return _has_core_package_part(module_name=module_name, package_part="infrastructure")


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


def _repository_lifecycle_call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name) and node.func.id in REPOSITORY_SESSION_FACTORY_CALLS:
        return node.func.id

    if isinstance(node.func, ast.Attribute) and node.func.attr in REPOSITORY_TRANSACTION_METHODS:
        return node.func.attr

    return None


def _is_service_module(module: SourceModule) -> bool:
    return (
        module.source_parts[0] == "core"
        and "infrastructure" not in module.source_parts
        and "delivery" not in module.source_parts
        and (module.path.name == "services.py" or "services" in module.source_parts)
    )


def _is_controller_module(module: SourceModule) -> bool:
    return _is_core_delivery_module(module) and "controllers" in module.source_parts


def _is_forbidden_controller_import(module_name: str) -> bool:
    return (
        module_name.startswith(FORBIDDEN_CONTROLLER_IMPORT_PREFIXES)
        or module_name == "fastapi_template.core.unit_of_work"
        or _is_core_local_infrastructure_import(module_name)
        or _has_core_package_part(module_name=module_name, package_part="repositories")
        or _has_core_package_part(module_name=module_name, package_part="models")
    )


def _has_core_package_part(*, module_name: str, package_part: str) -> bool:
    parts = module_name.split(".")
    return (
        len(parts) >= 3
        and parts[0] == "fastapi_template"
        and parts[1] == "core"
        and package_part in parts[2:]
    )


def _is_service_or_use_case_module(module: SourceModule) -> bool:
    return (
        module.source_parts[0] == "core"
        and "delivery" not in module.source_parts
        and "infrastructure" not in module.source_parts
        and ("use_cases" in module.source_parts or "services" in module.source_parts)
    )


def _injected_dependency_name(annotation: ast.expr) -> str | None:
    if not isinstance(annotation, ast.Subscript):
        return None

    return name_for_expression(annotation.slice)
