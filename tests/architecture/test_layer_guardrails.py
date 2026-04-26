import ast
from pathlib import Path

from tests.architecture._source import (
    SourceModule,
    base_names,
    has_base,
    iter_class_definitions,
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
CONTROLLER_BASES = {
    "BaseAsyncController",
    "BaseController",
    "BaseTransactionController",
}
CONTROLLER_NON_ENDPOINT_METHOD_NAMES = {"handle_exception", "register"}
DOMAIN_LOGIC_EXCLUDED_FILE_NAMES = {
    "__init__.py",
    "apps.py",
}
DJANGO_MODEL_BASE_NAMES = {
    "AbstractBaseUser",
    "AbstractUser",
    "Model",
}
DJANGO_RELATION_FIELD_NAMES = {
    "ForeignKey",
    "ManyToManyField",
    "OneToOneField",
}
SCHEMA_COLLECTION_RETURN_NAMES = {
    "Iterable",
    "Sequence",
    "list",
    "tuple",
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


def test_domain_logic_modules_do_not_import_delivery_modules() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_domain_logic_module(module)
        for import_reference in iter_imports(module)
        if ".delivery." in import_reference.module_name
    ]

    assert violations == [], (
        "Domain logic modules must not import delivery modules, schemas, controllers, "
        "tasks, auth, throttling, or other transport concerns."
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


def test_django_model_classes_live_in_model_modules() -> None:
    model_class_names = _django_model_class_names()
    violations = [
        f"{module.relative_path}:{class_node.lineno} {class_node.name}"
        for module in iter_source_modules()
        for class_node in iter_class_definitions(module)
        if _is_django_model_class(class_node, model_class_names)
        if not _is_django_model_module(module)
    ]

    assert violations == [], "Django model classes must live in models.py modules."


def test_django_models_do_not_import_behavior_or_outer_layers() -> None:
    violations = [
        _format_import_violation(module, import_reference.module_name, import_reference.line_number)
        for module in iter_source_modules()
        if _is_django_model_module(module)
        for import_reference in iter_imports(module)
        if _is_forbidden_django_model_import(import_reference.module_name)
    ]

    assert violations == [], (
        "Django models must not import use cases, services, delivery, entrypoints, "
        "or infrastructure."
    )


def test_user_model_relations_use_auth_user_model_setting() -> None:
    violations = [
        f"{module.relative_path}:{call_node.lineno} uses {ast.unparse(target)}"
        for module in iter_source_modules()
        if _is_django_model_module(module)
        for call_node in ast.walk(module.tree)
        if isinstance(call_node, ast.Call)
        if _is_django_relation_field_call(call_node)
        if (target := _django_relation_target(call_node)) is not None
        if _is_direct_user_model_relation_target(target)
    ]

    assert violations == [], (
        "Relations to the user model must use settings.AUTH_USER_MODEL, "
        "not the concrete User class or user.User string."
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


def test_http_exceptions_stay_in_fastapi_delivery_boundary() -> None:
    violations = [
        f"{module.relative_path}:{line_number} references HTTPException"
        for module in iter_source_modules()
        if not _is_delivery_framework_module(module, "fastapi")
        for node in ast.walk(module.tree)
        if (line_number := _http_exception_boundary_violation_line_number(node)) is not None
    ]

    assert violations == [], "HTTPException must stay in FastAPI delivery modules."


def test_status_code_keywords_use_named_status_constants() -> None:
    violations = [
        f"{module.relative_path}:{_line_number(keyword.value)} uses raw status_code={status_code}"
        for module in iter_source_modules()
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "status_code"
        if (status_code := _integer_literal_value(keyword.value)) is not None
    ]

    assert violations == [], (
        "status_code must use HTTPStatus or starlette.status constants, not raw integers."
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


def test_import_time_calls_stay_in_composition_modules_or_logger_setup() -> None:
    violations = [
        f"{module.relative_path}:{call_node.lineno} calls {ast.unparse(call_node.func)}"
        for module in iter_source_modules()
        if not _can_have_import_time_calls(module)
        for call_node in _iter_import_time_call_nodes(module.tree)
        if not _is_logger_setup_call(call_node)
    ]

    assert violations == [], (
        "Import-time calls must stay in composition modules, Django settings, "
        "Django URLConf, or logging.getLogger(__name__) setup."
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


def test_fastapi_routes_with_response_body_declare_response_model() -> None:
    violations = [
        violation
        for module in iter_source_modules()
        if _is_delivery_framework_module(module, "fastapi")
        for class_node in iter_class_definitions(module)
        for route_call in _iter_add_api_route_calls(class_node)
        for violation in _response_model_violations(
            module=module,
            class_node=class_node,
            route_call=route_call,
        )
    ]

    assert violations == [], (
        "FastAPI routes whose endpoint returns a response body must declare response_model."
    )


def test_controller_endpoint_return_types_are_delivery_schemas_or_none() -> None:
    violations = [
        (
            f"{module.relative_path}:{method_node.lineno} "
            f"{class_node.name}.{method_node.name} returns "
            f"{_return_annotation_name(method_node.returns)}"
        )
        for module in iter_source_modules()
        for class_node in iter_class_definitions(module)
        if _is_concrete_controller(class_node)
        for method_node in _iter_public_controller_endpoint_methods(class_node)
        if not _is_valid_controller_endpoint_return(method_node.returns)
    ]

    assert violations == [], (
        "Public controller endpoints must return delivery schemas or None, "
        "not DTOs, models, dicts, or Any."
    )


def test_controller_post_init_overrides_call_super_once() -> None:
    violations = [
        (
            f"{module.relative_path}:{post_init_method.lineno} "
            f"{class_node.name} calls super().__post_init__() "
            f"{_super_post_init_call_count(post_init_method)} times"
        )
        for module in iter_source_modules()
        for class_node in iter_class_definitions(module)
        if _is_concrete_controller(class_node)
        for post_init_method in [_post_init_method(class_node)]
        if post_init_method is not None
        if _super_post_init_call_count(post_init_method) != 1
    ]

    assert violations == [], (
        "Controllers overriding __post_init__ must call super().__post_init__() exactly once."
    )


def test_fastapi_controllers_are_registered_by_fastapi_factory() -> None:
    _, fastapi_factory = _fastapi_factory_class()
    injected_fields = _injected_field_names_by_type(fastapi_factory)
    registered_fields = _registered_controller_field_names(fastapi_factory)
    violations: list[str] = []

    for module, class_node in _iter_fastapi_controller_classes():
        field_name = injected_fields.get(class_node.name)
        if field_name is None:
            violations.append(
                f"{module.relative_path}:{class_node.lineno} "
                f"{class_node.name} is not injected into FastAPIFactory",
            )
            continue

        if field_name not in registered_fields:
            violations.append(
                f"{module.relative_path}:{class_node.lineno} "
                f"{class_node.name} is injected as {field_name} but not registered",
            )

    assert violations == [], (
        "Concrete FastAPI controllers must be injected into and registered by FastAPIFactory."
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


def _is_domain_logic_module(module: SourceModule) -> bool:
    return (
        _is_core_internal_module(module)
        and "migrations" not in module.source_parts
        and module.path.name not in DOMAIN_LOGIC_EXCLUDED_FILE_NAMES
    )


def _is_delivery_framework_module(module: SourceModule, framework_name: str) -> bool:
    parts = module.source_parts
    return "delivery" in parts and framework_name in parts


def _imports_concrete_core_domain(module_name: str) -> bool:
    if not module_name.startswith("fastdjango.core."):
        return False

    domain_name = module_name.removeprefix("fastdjango.core.").split(".", maxsplit=1)[0]
    return domain_name not in {"exceptions", "shared"}


def _django_model_class_names() -> set[str]:
    model_class_names = set(DJANGO_MODEL_BASE_NAMES)
    class_nodes = [
        class_node
        for module in iter_source_modules()
        for class_node in iter_class_definitions(module)
    ]

    while True:
        discovered_names = {
            class_node.name
            for class_node in class_nodes
            if class_node.name not in model_class_names
            if _is_django_model_class(class_node, model_class_names)
        }
        if not discovered_names:
            return model_class_names

        model_class_names.update(discovered_names)


def _is_django_model_class(class_node: ast.ClassDef, model_class_names: set[str]) -> bool:
    return not base_names(class_node).isdisjoint(model_class_names)


def _is_django_model_module(module: SourceModule) -> bool:
    return module.path.name == "models.py" and "migrations" not in module.source_parts


def _is_forbidden_django_model_import(module_name: str) -> bool:
    if module_name.startswith(("fastdjango.entrypoints", "fastdjango.infrastructure")):
        return True

    if ".delivery." in module_name:
        return True

    parts = module_name.split(".")
    return (
        len(parts) > 3
        and parts[0] == "fastdjango"
        and parts[1] == "core"
        and any(part in {"services", "use_cases"} for part in parts[3:])
    )


def _is_django_relation_field_call(call_node: ast.Call) -> bool:
    return _annotation_name(call_node.func) in DJANGO_RELATION_FIELD_NAMES


def _django_relation_target(call_node: ast.Call) -> ast.expr | None:
    if call_node.args:
        return call_node.args[0]

    return _keyword_value(call_node, "to")


def _is_direct_user_model_relation_target(expression: ast.expr) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id == "User"

    if isinstance(expression, ast.Attribute):
        return expression.attr == "User"

    if isinstance(expression, ast.Call):
        return _annotation_name(expression.func) == "get_user_model"

    return (
        isinstance(expression, ast.Constant)
        and isinstance(expression.value, str)
        and (expression.value == "User" or expression.value.endswith(".User"))
    )


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


def _can_have_import_time_calls(module: SourceModule) -> bool:
    if module.source_parts[0] == "entrypoints" and module.path.name in {
        "app.py",
        "bootstrap.py",
    }:
        return True

    return module.source_parts in {
        ("entrypoints", "django", "urls.py"),
        ("infrastructure", "django", "settings.py"),
    }


def _is_under(module: SourceModule, *parts: str) -> bool:
    return module.source_parts[: len(parts)] == parts


def _format_import_violation(
    module: SourceModule,
    import_module_name: str,
    line_number: int,
) -> str:
    return f"{module.relative_path}:{line_number} imports {import_module_name}"


def _is_http_exception_import(node: ast.AST) -> bool:
    if isinstance(node, ast.ImportFrom):
        return any(alias.name == "HTTPException" for alias in node.names)

    if isinstance(node, ast.Import):
        return any(alias.name.endswith(".HTTPException") for alias in node.names)

    return False


def _is_http_exception_reference(node: ast.AST) -> bool:
    return (isinstance(node, ast.Name) and node.id == "HTTPException") or (
        isinstance(node, ast.Attribute) and node.attr == "HTTPException"
    )


def _http_exception_boundary_violation_line_number(node: ast.AST) -> int | None:
    if _is_http_exception_import(node) or _is_http_exception_reference(node):
        return _line_number(node)

    return None


def _line_number(node: ast.AST) -> int:
    return node.lineno if isinstance(node, ast.stmt | ast.expr) else 0


def _integer_literal_value(node: ast.expr) -> int | None:
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value

    return None


def _iter_import_time_call_nodes(tree: ast.Module) -> list[ast.Call]:
    return [
        call_node
        for statement in tree.body
        for call_node in _iter_statement_import_time_call_nodes(statement)
    ]


def _iter_statement_import_time_call_nodes(statement: ast.stmt) -> list[ast.Call]:
    if isinstance(statement, ast.Import | ast.ImportFrom | ast.ClassDef):
        return []

    if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef):
        return []

    if isinstance(statement, ast.If) and _is_non_import_time_if_test(statement.test):
        return [
            call_node
            for nested_statement in statement.orelse
            for call_node in _iter_statement_import_time_call_nodes(nested_statement)
        ]

    visitor = _ImportTimeCallVisitor()
    visitor.visit(statement)
    return visitor.calls


def _is_non_import_time_if_test(expression: ast.expr) -> bool:
    return _is_type_checking_test(expression) or _is_main_guard_test(expression)


def _is_type_checking_test(expression: ast.expr) -> bool:
    return (isinstance(expression, ast.Name) and expression.id == "TYPE_CHECKING") or (
        isinstance(expression, ast.Attribute) and expression.attr == "TYPE_CHECKING"
    )


def _is_main_guard_test(expression: ast.expr) -> bool:
    return (
        isinstance(expression, ast.Compare)
        and isinstance(expression.left, ast.Name)
        and expression.left.id == "__name__"
        and len(expression.ops) == 1
        and isinstance(expression.ops[0], ast.Eq)
        and len(expression.comparators) == 1
        and isinstance(expression.comparators[0], ast.Constant)
        and expression.comparators[0].value == "__main__"
    )


def _is_logger_setup_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "getLogger"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "logging"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "__name__"
        and not node.keywords
    )


class _ImportTimeCallVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: list[ast.Call] = []

    def visit_Call(self, node: ast.Call) -> None:
        self.calls.append(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return


def _is_concrete_controller(class_node: ast.ClassDef) -> bool:
    return not class_node.name.startswith("Base") and has_base(class_node, CONTROLLER_BASES)


def _iter_public_controller_endpoint_methods(
    class_node: ast.ClassDef,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        statement
        for statement in class_node.body
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
        if not statement.name.startswith("_")
        if statement.name not in CONTROLLER_NON_ENDPOINT_METHOD_NAMES
    ]


def _is_valid_controller_endpoint_return(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False

    if _is_none_annotation(annotation):
        return True

    if _annotation_name(annotation).endswith("Schema"):
        return True

    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return _is_valid_controller_endpoint_return(
            annotation.left,
        ) and _is_valid_controller_endpoint_return(annotation.right)

    if isinstance(annotation, ast.Subscript):
        return _is_valid_schema_collection_return(annotation)

    return False


def _is_valid_schema_collection_return(annotation: ast.Subscript) -> bool:
    return _annotation_name(
        annotation.value,
    ) in SCHEMA_COLLECTION_RETURN_NAMES and _is_schema_slice(annotation.slice)


def _is_schema_slice(annotation: ast.expr) -> bool:
    if isinstance(annotation, ast.Tuple):
        return all(
            (isinstance(element, ast.Constant) and element.value is Ellipsis)
            or _is_valid_controller_endpoint_return(element)
            for element in annotation.elts
        )

    return _is_valid_controller_endpoint_return(annotation)


def _annotation_name(annotation: ast.expr) -> str:
    if isinstance(annotation, ast.Name):
        return annotation.id

    if isinstance(annotation, ast.Attribute):
        return annotation.attr

    if isinstance(annotation, ast.Subscript):
        return _annotation_name(annotation.value)

    return ""


def _return_annotation_name(annotation: ast.expr | None) -> str:
    if annotation is None:
        return "missing annotation"

    return ast.unparse(annotation)


def _post_init_method(
    class_node: ast.ClassDef,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    return _class_method_map(class_node).get("__post_init__")


def _super_post_init_call_count(
    method_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> int:
    return sum(
        1
        for node in ast.walk(method_node)
        if isinstance(node, ast.Call)
        if _is_super_post_init_call(node)
    )


def _is_super_post_init_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "__post_init__"
        and isinstance(node.func.value, ast.Call)
        and isinstance(node.func.value.func, ast.Name)
        and node.func.value.func.id == "super"
        and not node.func.value.args
        and not node.func.value.keywords
    )


def _iter_fastapi_controller_classes() -> list[tuple[SourceModule, ast.ClassDef]]:
    return [
        (module, class_node)
        for module in iter_source_modules()
        if _is_core_fastapi_controller_module(module)
        for class_node in iter_class_definitions(module)
        if _is_concrete_controller(class_node)
    ]


def _is_core_fastapi_controller_module(module: SourceModule) -> bool:
    return (
        module.source_parts[0] == "core"
        and module.path.name == "controllers.py"
        and _is_delivery_framework_module(module, "fastapi")
    )


def _fastapi_factory_class() -> tuple[SourceModule, ast.ClassDef]:
    for module in iter_source_modules():
        if module.source_parts != ("entrypoints", "fastapi", "factories.py"):
            continue

        for class_node in iter_class_definitions(module):
            if class_node.name == "FastAPIFactory":
                return module, class_node

    msg = "FastAPIFactory was not found."
    raise AssertionError(msg)


def _injected_field_names_by_type(class_node: ast.ClassDef) -> dict[str, str]:
    fields: dict[str, str] = {}
    for statement in class_node.body:
        if not (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and isinstance(statement.annotation, ast.Subscript)
            and _annotation_name(statement.annotation.value) == "Injected"
        ):
            continue

        injected_type_name = _annotation_name(statement.annotation.slice)
        if injected_type_name:
            fields[injected_type_name] = statement.target.id

    return fields


def _registered_controller_field_names(class_node: ast.ClassDef) -> set[str]:
    register_method = _class_method_map(class_node).get("_register_controllers")
    if register_method is None:
        return set()

    return {
        node.func.value.attr
        for node in ast.walk(register_method)
        if isinstance(node, ast.Call)
        if isinstance(node.func, ast.Attribute)
        if node.func.attr == "register"
        if isinstance(node.func.value, ast.Attribute)
        if isinstance(node.func.value.value, ast.Name)
        if node.func.value.value.id == "self"
    }


def _iter_add_api_route_calls(class_node: ast.ClassDef) -> list[ast.Call]:
    return [
        node
        for statement in class_node.body
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
        if statement.name == "register"
        for node in ast.walk(statement)
        if isinstance(node, ast.Call)
        if isinstance(node.func, ast.Attribute)
        if node.func.attr == "add_api_route"
    ]


def _response_model_violations(
    *,
    module: SourceModule,
    class_node: ast.ClassDef,
    route_call: ast.Call,
) -> list[str]:
    endpoint_name = _self_endpoint_name(_keyword_value(route_call, "endpoint"))
    if endpoint_name is None:
        return []

    endpoint = _class_method_map(class_node).get(endpoint_name)
    if (
        endpoint is None
        or endpoint.returns is None
        or _is_none_annotation(endpoint.returns)
        or _has_non_none_keyword(route_call, "response_model")
    ):
        return []

    return [
        (
            f"{module.relative_path}:{route_call.lineno} {class_node.name}.{endpoint.name} "
            f"returns {ast.unparse(endpoint.returns)} without response_model"
        ),
    ]


def _keyword_value(call: ast.Call, keyword_name: str) -> ast.expr | None:
    return next(
        (keyword.value for keyword in call.keywords if keyword.arg == keyword_name),
        None,
    )


def _self_endpoint_name(expression: ast.expr | None) -> str | None:
    if (
        isinstance(expression, ast.Attribute)
        and isinstance(expression.value, ast.Name)
        and expression.value.id == "self"
    ):
        return expression.attr

    return None


def _class_method_map(
    class_node: ast.ClassDef,
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        statement.name: statement
        for statement in class_node.body
        if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def _is_none_annotation(annotation: ast.expr) -> bool:
    return isinstance(annotation, ast.Constant) and annotation.value is None


def _has_non_none_keyword(call: ast.Call, keyword_name: str) -> bool:
    keyword_value = _keyword_value(call, keyword_name)
    return keyword_value is not None and not _is_none_annotation(keyword_value)


def _decorator_name(decorator: ast.expr) -> str | None:
    decorator = decorator.func if isinstance(decorator, ast.Call) else decorator
    if isinstance(decorator, ast.Attribute):
        return decorator.attr

    if isinstance(decorator, ast.Name):
        return decorator.id

    return None
