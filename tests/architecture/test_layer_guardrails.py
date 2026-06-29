import ast

from tests.architecture._source import (
    SOURCE_ROOT,
    SourceModule,
    has_base,
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
FRAMEWORK_IMPORT_PREFIXES = ("fastapi", "starlette")
DATABASE_QUERY_FUNCTION_NAMES = {"delete", "insert", "select", "text", "update"}
ROUTE_REGISTRY_FUNCTION_NAMES = {"add_api_route", "add_api_websocket_route"}
ROUTER_PREFIX_FUNCTION_NAMES = {"APIRouter", "include_router"}
REPOSITORY_TRANSACTION_METHODS = {
    "begin",
    "close",
    "commit",
    "rollback",
}
REPOSITORY_SESSION_FACTORY_CALLS = {"async_sessionmaker", "create_async_engine"}
FORBIDDEN_DELIVERY_IMPORT_PREFIXES = (
    "sqlalchemy",
    "fastapi_template.infrastructure.sqlalchemy.unit_of_work",
)
SQLALCHEMY_TRANSACTION_LIFECYCLE_SOURCE_PARTS = {
    ("infrastructure", "sqlalchemy", "session.py"),
    ("infrastructure", "sqlalchemy", "unit_of_work.py"),
}
TRANSACTION_LIFECYCLE_RECEIVER_NAMES = {
    "_connection",
    "_engine",
    "_session",
    "connection",
    "engine",
    "session",
    "transaction",
}
USE_CASE_BASES = {"BaseUseCase"}


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
    violations: list[str] = []
    for module in iter_source_modules():
        model_class_names = _model_class_names(module=module)
        if not model_class_names:
            continue

        if not _is_local_sqlalchemy_model_module(module):
            violations.append(f"{module.relative_path} defines {model_class_names}")
            continue

        if len(model_class_names) != 1:
            violations.append(f"{module.relative_path} defines {model_class_names}")
            continue

        expected_stem = _model_file_stem(model_name=model_class_names[0])
        if module.path.stem != expected_stem:
            violations.append(
                f"{module.relative_path} should be named {expected_stem}.py",
            )

    assert violations == [], (
        "SQLAlchemy models must live in scoped local SQLAlchemy model modules, "
        "one table/domain model per file."
    )


def test_sqlalchemy_model_guardrail_accepts_structural_model_paths() -> None:
    module = _source_module_from_text(
        source_parts=(
            "core",
            "billing",
            "infrastructure",
            "sqlalchemy",
            "models",
            "invoice.py",
        ),
        source="class InvoiceModel: ...",
    )

    assert _is_local_sqlalchemy_model_module(module)
    assert _model_class_names(module=module) == ["InvoiceModel"]
    assert _model_file_stem(model_name="InvoiceModel") == "invoice"


def test_sqlalchemy_model_guardrail_rejects_bucket_model_paths() -> None:
    module = _source_module_from_text(
        source_parts=(
            "core",
            "billing",
            "infrastructure",
            "sqlalchemy",
            "models.py",
        ),
        source="class InvoiceModel: ...",
    )

    assert not _is_local_sqlalchemy_model_module(module)


def test_route_path_guardrail_catches_positional_paths_and_router_prefixes() -> None:
    legacy_health_path = "/v1/" + "health"
    positional_route = _call_from_expression(
        f"registry.add_api_route({legacy_health_path!r}, endpoint=health)",
    )
    router_prefix = _call_from_expression("fastapi.APIRouter(prefix='/api/v1')")
    include_prefix = _call_from_expression("app.include_router(router, prefix='/api/v1')")

    assert _route_path_values(positional_route) == [legacy_health_path]
    assert _route_prefix_values(router_prefix) == ["/api/v1"]
    assert _route_prefix_values(include_prefix) == ["/api/v1"]


def test_database_query_guardrail_catches_sqlalchemy_alias_calls() -> None:
    module = _source_module_from_text(
        source_parts=(
            "core",
            "billing",
            "infrastructure",
            "sqlalchemy",
            "mappers",
            "invoice.py",
        ),
        source="""
import sqlalchemy
import sqlalchemy as sa
from sqlalchemy import delete as sa_delete

sqlalchemy.select(InvoiceModel)
sa.update(InvoiceModel)
sa_delete(InvoiceModel)
""",
    )
    query_calls = [
        _database_query_call_name(
            node,
            query_function_names=_database_query_function_names(module=module),
            sqlalchemy_module_names=_sqlalchemy_module_names(module=module),
        )
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
    ]

    assert query_calls == ["select", "update", "sa_delete"]


def test_unit_of_work_scope_guardrail_catches_renamed_dependencies() -> None:
    module = _source_module_from_text(
        source_parts=("core", "user", "services", "example.py"),
        source="""
class ExampleService:
    _unit_of_work: Injected[UnitOfWork]

    async def run(self) -> None:
        async with self._unit_of_work as active_uow:
            pass
""",
    )

    assert _service_uow_scope_violations(module=module) == [
        "src/fastapi_template/core/user/services/example.py:5 opens UnitOfWork scope",
    ]


def test_use_case_scope_guardrail_accepts_renamed_execute_dependency() -> None:
    module = _source_module_from_text(
        source_parts=("core", "user", "use_cases", "example.py"),
        source="""
class ExampleUseCase(BaseUseCase):
    _unit_of_work: Injected[UnitOfWork]

    async def execute(self) -> None:
        async with self._unit_of_work as active_uow:
            pass
""",
    )

    assert _use_case_uow_scope_violations(module=module) == []


def test_database_query_execution_stays_in_local_sqlalchemy_adapters() -> None:
    violations = [
        f"{module.relative_path}:{node.lineno} calls {call_name}"
        for module in iter_source_modules()
        if not _can_execute_sqlalchemy_queries(module)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
        if (
            call_name := _database_query_call_name(
                node,
                query_function_names=_database_query_function_names(module=module),
                sqlalchemy_module_names=_sqlalchemy_module_names(module=module),
            )
        )
        is not None
    ]

    assert violations == [], (
        "Runtime SQLAlchemy query construction and execution must stay in local "
        "SQLAlchemy adapters."
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


def test_transaction_lifecycle_stays_in_sqlalchemy_wiring() -> None:
    violations = [
        f"{module.relative_path}:{node.lineno} calls {call_name}"
        for module in iter_source_modules()
        if module.source_parts not in SQLALCHEMY_TRANSACTION_LIFECYCLE_SOURCE_PARTS
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
        if (call_name := _repository_lifecycle_call_name(node)) is not None
    ]

    assert violations == [], (
        "Only shared SQLAlchemy session and UnitOfWork wiring may commit, rollback, "
        "close sessions, begin transactions, or create session factories."
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


def test_shared_infrastructure_modules_do_not_import_core_delivery() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_shared_infrastructure_module(module)
        for import_reference in iter_imports(module)
        if _is_core_delivery_import(import_reference.module_name)
    ]

    assert violations == [], "Shared infrastructure must not import core delivery modules."


def test_delivery_modules_do_not_import_local_infrastructure() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_core_delivery_module(module)
        for import_reference in iter_imports(module)
        if _is_core_local_infrastructure_import(import_reference.module_name)
    ]

    assert violations == [], "Delivery adapters must not import local infrastructure modules."


def test_delivery_modules_do_not_import_repositories_or_uow_implementations() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_core_delivery_module(module)
        for import_reference in iter_imports(module)
        if _is_forbidden_delivery_import(import_reference.module_name)
    ]

    assert violations == [], (
        "Delivery modules must not import repositories, UoW implementations, SQLAlchemy, "
        "SQLAlchemy models, or local infrastructure."
    )


def test_services_do_not_open_unit_of_work_scopes() -> None:
    violations = [
        violation
        for module in iter_source_modules()
        if _is_service_module(module)
        for violation in _service_uow_scope_violations(module=module)
    ]

    assert violations == [], "Services may receive an active UoW, but must not open UoW scopes."


def test_use_cases_open_at_most_one_unit_of_work_scope_inside_execute() -> None:
    violations = [
        violation
        for module in iter_source_modules()
        if _is_use_case_module(module)
        for violation in _use_case_uow_scope_violations(module=module)
    ]

    assert violations == [], (
        "Use cases may open at most one UnitOfWork scope, and only inside execute()."
    )


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
        if _is_fastapi_route_module(module)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
        for path in _route_path_values(node)
        if not path.startswith("/api/v1/")
    ]
    violations.extend(
        f"{module.relative_path}:{node.lineno} prefix={prefix!r}"
        for module in iter_source_modules()
        if _is_fastapi_route_module(module)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
        for prefix in _route_prefix_values(node)
        if prefix
    )

    assert violations == [], (
        "Public FastAPI route paths must be full /api/v1/... paths without router prefixes."
    )


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
    assert _is_forbidden_delivery_import("fastapi_template.core.user.repositories")
    assert _is_forbidden_delivery_import("fastapi_template.core.user.repositories.user")
    assert _is_forbidden_delivery_import(
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


def _is_shared_infrastructure_module(module: SourceModule) -> bool:
    return module.source_parts[0] == "infrastructure"


def _is_core_delivery_module(module: SourceModule) -> bool:
    return module.source_parts[0] == "core" and "delivery" in module.source_parts


def _is_local_sqlalchemy_adapter_module(module: SourceModule) -> bool:
    parts = module.source_parts
    return len(parts) >= 5 and parts[0] == "core" and parts[2:4] == ("infrastructure", "sqlalchemy")


def _is_local_sqlalchemy_model_module(module: SourceModule) -> bool:
    parts = module.source_parts
    return (
        len(parts) == 6
        and parts[0] == "core"
        and parts[2:5] == ("infrastructure", "sqlalchemy", "models")
        and parts[-1] != "__init__.py"
    )


def _is_local_sqlalchemy_repository_module(module: SourceModule) -> bool:
    return _is_local_sqlalchemy_adapter_module(module) and "repositories" in module.source_parts


def _can_execute_sqlalchemy_queries(module: SourceModule) -> bool:
    return _is_local_sqlalchemy_repository_module(module) or module.source_parts == (
        "core",
        "health",
        "infrastructure",
        "sqlalchemy",
        "health_checker.py",
    )


def _is_repository_port_module(module: SourceModule) -> bool:
    return (
        module.source_parts[0] == "core"
        and "repositories" in module.source_parts
        and "infrastructure" not in module.source_parts
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


def _is_fastapi_route_module(module: SourceModule) -> bool:
    return _is_fastapi_delivery_module(module) or module.source_parts[0] == "entrypoints"


def _route_path_values(node: ast.Call) -> list[str]:
    if name_for_expression(node.func) not in ROUTE_REGISTRY_FUNCTION_NAMES:
        return []

    paths = []
    if node.args:
        paths.append(_string_value(node.args[0]))
    paths.extend(_string_value(keyword.value) for keyword in node.keywords if keyword.arg == "path")

    return [path for path in paths if path is not None]


def _route_prefix_values(node: ast.Call) -> list[str]:
    if name_for_expression(node.func) not in ROUTER_PREFIX_FUNCTION_NAMES:
        return []

    return [
        prefix
        for keyword in node.keywords
        if keyword.arg == "prefix"
        if (prefix := _string_value(keyword.value)) is not None
    ]


def _string_value(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    return "<dynamic>"


def _can_access_container(module: SourceModule) -> bool:
    return module.source_parts[0] in {"entrypoints", "ioc"}


def _model_class_names(*, module: SourceModule) -> list[str]:
    return [
        node.name
        for node in ast.walk(module.tree)
        if isinstance(node, ast.ClassDef) and node.name.endswith("Model")
    ]


def _model_file_stem(*, model_name: str) -> str:
    base_name = model_name.removesuffix("Model")
    snake_name = ""
    for character in base_name:
        if character.isupper() and snake_name:
            snake_name = f"{snake_name}_"
        snake_name = f"{snake_name}{character.lower()}"

    return snake_name


def _database_query_call_name(
    node: ast.Call,
    *,
    query_function_names: set[str],
    sqlalchemy_module_names: set[str],
) -> str | None:
    if isinstance(node.func, ast.Name) and node.func.id in query_function_names:
        return node.func.id

    if not isinstance(node.func, ast.Attribute):
        return None

    if (
        node.func.attr in DATABASE_QUERY_FUNCTION_NAMES
        and name_for_expression(node.func.value) in sqlalchemy_module_names
    ):
        return node.func.attr

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


def _database_query_function_names(*, module: SourceModule) -> set[str]:
    query_function_names = set(DATABASE_QUERY_FUNCTION_NAMES)
    query_function_names.update(
        alias.asname or alias.name
        for node in module.tree.body
        if isinstance(node, ast.ImportFrom)
        if node.module == "sqlalchemy"
        for alias in node.names
        if alias.name in DATABASE_QUERY_FUNCTION_NAMES
    )
    return query_function_names


def _sqlalchemy_module_names(*, module: SourceModule) -> set[str]:
    return {
        alias.asname or alias.name
        for node in module.tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name == "sqlalchemy"
    }


def _repository_lifecycle_call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name) and node.func.id in REPOSITORY_SESSION_FACTORY_CALLS:
        return node.func.id

    if (
        isinstance(node.func, ast.Attribute)
        and node.func.attr in REPOSITORY_TRANSACTION_METHODS
        and name_for_expression(node.func.value) in TRANSACTION_LIFECYCLE_RECEIVER_NAMES
    ):
        return node.func.attr

    return None


def _is_service_module(module: SourceModule) -> bool:
    return (
        module.source_parts[0] == "core"
        and "infrastructure" not in module.source_parts
        and "delivery" not in module.source_parts
        and (module.path.name == "services.py" or "services" in module.source_parts)
    )


def _service_uow_scope_violations(*, module: SourceModule) -> list[str]:
    violations: list[str] = []
    for class_node in (node for node in ast.walk(module.tree) if isinstance(node, ast.ClassDef)):
        class_uow_names = _class_unit_of_work_field_names(class_node=class_node)
        for method_node in _class_methods(class_node=class_node):
            method_uow_names = class_uow_names | _method_unit_of_work_parameter_names(
                method_node=method_node,
            )
            violations.extend(
                f"{module.relative_path}:{node.lineno} opens UnitOfWork scope"
                for node in _method_uow_scope_nodes(
                    method_node=method_node,
                    uow_names=method_uow_names,
                )
            )

    return violations


def _is_use_case_module(module: SourceModule) -> bool:
    return (
        module.source_parts[0] == "core"
        and "infrastructure" not in module.source_parts
        and "delivery" not in module.source_parts
        and "use_cases" in module.source_parts
    )


def _use_case_uow_scope_violations(*, module: SourceModule) -> list[str]:
    violations: list[str] = []
    for class_node in (
        node
        for node in ast.walk(module.tree)
        if isinstance(node, ast.ClassDef) and has_base(node, USE_CASE_BASES)
    ):
        class_uow_names = _class_unit_of_work_field_names(class_node=class_node)
        scope_count = 0
        for method_node in _class_methods(class_node=class_node):
            method_uow_names = class_uow_names | _method_unit_of_work_parameter_names(
                method_node=method_node,
            )
            method_scope_count = _method_uow_scope_count(
                method_node=method_node,
                uow_names=method_uow_names,
            )
            scope_count += method_scope_count
            if method_scope_count and method_node.name != "execute":
                violations.append(
                    f"{module.relative_path}:{method_node.lineno} "
                    f"{class_node.name}.{method_node.name} opens UnitOfWork scope",
                )

        if scope_count > 1:
            violations.append(
                f"{module.relative_path}:{class_node.lineno} opens {scope_count} UoWs",
            )

    return violations


def _class_methods(*, class_node: ast.ClassDef) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node for node in class_node.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]


def _method_uow_scope_count(
    *,
    method_node: ast.FunctionDef | ast.AsyncFunctionDef,
    uow_names: set[str],
) -> int:
    return len(_method_uow_scope_nodes(method_node=method_node, uow_names=uow_names))


def _method_uow_scope_nodes(
    *,
    method_node: ast.FunctionDef | ast.AsyncFunctionDef,
    uow_names: set[str],
) -> list[ast.AsyncWith]:
    return [
        node
        for node in ast.walk(method_node)
        if isinstance(node, ast.AsyncWith)
        for item in node.items
        if name_for_expression(item.context_expr) in uow_names
    ]


def _class_unit_of_work_field_names(*, class_node: ast.ClassDef) -> set[str]:
    return {
        node.target.id
        for node in class_node.body
        if isinstance(node, ast.AnnAssign)
        if isinstance(node.target, ast.Name)
        if _is_unit_of_work_annotation(node.annotation)
    }


def _method_unit_of_work_parameter_names(
    *,
    method_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    return {
        argument.arg
        for argument in (*method_node.args.args, *method_node.args.kwonlyargs)
        if argument.annotation is not None
        if _is_unit_of_work_annotation(argument.annotation)
    }


def _is_unit_of_work_annotation(annotation: ast.expr) -> bool:
    return (
        name_for_expression(annotation) == "UnitOfWork"
        or _injected_dependency_name(annotation) == "UnitOfWork"
    )


def _is_forbidden_delivery_import(module_name: str) -> bool:
    return (
        module_name.startswith(FORBIDDEN_DELIVERY_IMPORT_PREFIXES)
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


def _source_module_from_text(*, source_parts: tuple[str, ...], source: str) -> SourceModule:
    path = SOURCE_ROOT.joinpath(*source_parts)
    return SourceModule(
        path=path,
        tree=ast.parse(source.lstrip(), filename=str(path)),
    )


def _call_from_expression(source: str) -> ast.Call:
    module = ast.parse(source)
    expression = module.body[0]
    if not isinstance(expression, ast.Expr) or not isinstance(expression.value, ast.Call):
        raise TypeError(source)

    return expression.value
