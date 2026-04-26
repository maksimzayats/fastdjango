import ast
from pathlib import Path

from tests.architecture._source import (
    SourceModule,
    iter_imports,
    iter_source_modules,
)

CORE_DELIVERY_IMPORT_EXEMPTIONS = {
    (
        Path("src/fastdjango/core/user/apps.py"),
        "fastdjango.core.user.delivery.django",
    ),
}
ENVIRONMENT_ACCESS_FILE_NAMES = {"configurator.py", "manage.py", "settings.py"}
ROUTE_DECORATOR_NAMES = {
    "api_route",
    "delete",
    "get",
    "patch",
    "post",
    "put",
    "route",
    "websocket",
}


def test_foundation_layer_has_no_outward_dependencies() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if module.source_parts[0] == "foundation"
        for import_reference in iter_imports(module)
        if not import_reference.is_type_checking
        if import_reference.module_name.startswith(
            (
                "fastdjango.core",
                "fastdjango.entrypoints",
                "fastdjango.infrastructure",
                "fastdjango.ioc",
            ),
        )
    ]

    assert violations == [], "Foundation must not depend on outer application layers."


def test_core_domain_internals_do_not_import_delivery_or_composition_layers() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_core_internal_module(module)
        for import_reference in iter_imports(module)
        if not import_reference.is_type_checking
        if _is_forbidden_core_internal_import(module, import_reference.module_name)
    ]

    assert violations == [], (
        "Core domain internals must not import delivery, infrastructure, entrypoints, or IoC."
    )


def test_infrastructure_does_not_depend_on_domain_delivery_or_entrypoints() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if module.source_parts[0] == "infrastructure"
        for import_reference in iter_imports(module)
        if not import_reference.is_type_checking
        if _is_core_delivery_module(import_reference.module_name)
        or import_reference.module_name.startswith("fastdjango.entrypoints")
    ]

    assert violations == [], (
        "Infrastructure may integrate frameworks, but must not depend on delivery modules "
        "or entrypoint composition."
    )


def test_shared_core_module_stays_domain_neutral() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_under(module, "core", "shared")
        for import_reference in iter_imports(module)
        if not import_reference.is_type_checking
        if _imports_concrete_core_domain(import_reference.module_name)
    ]

    assert violations == [], "core.shared must not import concrete core domains."


def test_django_orm_access_stays_in_domain_behavior_modules() -> None:
    violations = [
        f"{module.relative_path}:{node.lineno} uses .objects"
        for module in iter_source_modules()
        if not _can_access_django_orm(module)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Attribute)
        if node.attr == "objects"
    ]

    assert violations == [], (
        "Django ORM access belongs in services, use cases, models, admin, and migrations."
    )


def test_framework_imports_stay_in_framework_specific_layers() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        for import_reference in iter_imports(module)
        if not import_reference.is_type_checking
        if _is_forbidden_framework_import(module, import_reference.module_name)
    ]

    assert violations == [], (
        "FastAPI/Starlette and Celery imports must stay in their delivery, entrypoint, "
        "or infrastructure integration layers."
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
        if not import_reference.is_type_checking
        if import_reference.module_name.startswith("fastdjango.ioc")
    )

    assert violations == [], "Only composition roots may access the IoC container."


def test_direct_environment_access_stays_in_settings_or_configurators() -> None:
    violations = [
        f"{module.relative_path}:{node.lineno} accesses os.{node.attr}"
        for module in iter_source_modules()
        if not _can_access_environment(module)
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Attribute)
        if isinstance(node.value, ast.Name)
        if node.value.id == "os"
        if node.attr in {"environ", "getenv"}
    ]

    assert violations == [], (
        "Direct environment access must stay in settings, configurators, or composition roots."
    )


def test_routes_are_registered_through_controller_register_methods() -> None:
    violations = [
        f"{module.relative_path}:{node.lineno} uses @{decorator_name}"
        for module in iter_source_modules()
        for node in ast.walk(module.tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        for decorator in node.decorator_list
        if (decorator_name := _decorator_name(decorator)) in ROUTE_DECORATOR_NAMES
    ]

    assert violations == [], (
        "Routes must be registered in controller register() methods, not through "
        "function decorators."
    )


def _is_forbidden_core_internal_import(module: SourceModule, module_name: str) -> bool:
    if module_name.startswith(
        ("fastdjango.entrypoints", "fastdjango.infrastructure", "fastdjango.ioc"),
    ):
        return True

    if ".delivery." not in module_name:
        return False

    return not _is_exempt_core_delivery_import(module, module_name)


def _is_core_delivery_module(module_name: str) -> bool:
    return module_name.startswith("fastdjango.core.") and ".delivery." in module_name


def _is_exempt_core_delivery_import(module: SourceModule, module_name: str) -> bool:
    relative_path = module.relative_path
    return any(
        relative_path == exempt_path and module_name.startswith(exempt_module)
        for exempt_path, exempt_module in CORE_DELIVERY_IMPORT_EXEMPTIONS
    )


def _is_forbidden_framework_import(module: SourceModule, module_name: str) -> bool:
    if module_name.startswith(("fastapi", "starlette")):
        return not (
            _is_under(module, "entrypoints", "fastapi")
            or _is_delivery_framework_module(module, "fastapi")
            or module.source_parts[0] == "infrastructure"
        )

    if module_name.startswith("celery"):
        return not (
            _is_under(module, "entrypoints", "celery")
            or _is_delivery_framework_module(module, "celery")
            or _is_under(module, "infrastructure", "celery")
        )

    return False


def _is_core_internal_module(module: SourceModule) -> bool:
    return module.source_parts[0] == "core" and "delivery" not in module.source_parts


def _is_delivery_framework_module(module: SourceModule, framework_name: str) -> bool:
    parts = module.source_parts
    return "delivery" in parts and framework_name in parts


def _imports_concrete_core_domain(module_name: str) -> bool:
    if not module_name.startswith("fastdjango.core."):
        return False

    domain_name = module_name.removeprefix("fastdjango.core.").split(".", maxsplit=1)[0]
    return domain_name not in {"exceptions", "shared"}


def _can_access_django_orm(module: SourceModule) -> bool:
    return (
        module.path.name in {"admin.py", "models.py", "use_cases.py"}
        or "migrations" in module.source_parts
        or "services" in module.source_parts
    )


def _can_access_container(module: SourceModule) -> bool:
    return module.source_parts[0] in {"entrypoints", "ioc"} or module.path.name == "manage.py"


def _can_access_environment(module: SourceModule) -> bool:
    return module.path.name in ENVIRONMENT_ACCESS_FILE_NAMES or module.source_parts[0] in {
        "entrypoints",
        "ioc",
    }


def _is_under(module: SourceModule, *parts: str) -> bool:
    return module.source_parts[: len(parts)] == parts


def _format_import_violation(
    module: SourceModule,
    import_module_name: str,
    line_number: int,
) -> str:
    return f"{module.relative_path}:{line_number} imports {import_module_name}"


def _decorator_name(decorator: ast.expr) -> str | None:
    decorator = decorator.func if isinstance(decorator, ast.Call) else decorator
    if isinstance(decorator, ast.Attribute):
        return decorator.attr

    if isinstance(decorator, ast.Name):
        return decorator.id

    return None
