import ast
from dataclasses import dataclass
from pathlib import Path

from tests.architecture._source import (
    SourceModule,
    base_names,
    iter_class_definitions,
    iter_imports,
    iter_source_modules,
    name_for_expression,
)

DJANGO_MODEL_BASE_NAMES = {
    "AbstractBaseUser",
    "AbstractUser",
    "Model",
}


@dataclass(frozen=True)
class DomainModel:
    domain_name: str
    module: SourceModule
    class_node: ast.ClassDef

    @property
    def model_name(self) -> str:
        return self.class_node.name


def test_concrete_django_models_are_registered_in_domain_admin() -> None:
    admin_registrations = _admin_registrations_by_domain()
    violations = [
        f"{model.module.relative_path}:{model.class_node.lineno} {model.model_name}"
        for model in _iter_domain_models()
        if model.model_name not in admin_registrations.get(model.domain_name, set())
    ]

    assert violations == [], (
        "Concrete Django models must be registered in their domain delivery/django/admin.py."
    )


def test_django_admin_classes_define_list_display() -> None:
    violations = [
        f"{module.relative_path}:{class_node.lineno} {class_node.name}"
        for module in _iter_admin_modules()
        for class_node in iter_class_definitions(module)
        if _is_model_admin_class(class_node)
        if not _class_assigns_non_empty_sequence(class_node, "list_display")
    ]

    assert violations == [], "Django ModelAdmin classes must define non-empty list_display."


def test_domain_app_configs_import_django_admin_modules() -> None:
    violations = [
        f"{admin_path.relative_to(_repo_root())}"
        for admin_path in _iter_admin_paths()
        if not _domain_apps_imports_admin(admin_path)
    ]

    assert violations == [], (
        "Domain AppConfig.ready() must import its delivery/django/admin.py module "
        "so Django registers admin classes."
    )


def _iter_domain_models() -> list[DomainModel]:
    return [
        DomainModel(
            domain_name=module.source_parts[1],
            module=module,
            class_node=class_node,
        )
        for module in iter_source_modules()
        if module.source_parts[:1] == ("core",)
        if module.path.name == "models.py"
        for class_node in iter_class_definitions(module)
        if _is_concrete_django_model(class_node)
    ]


def _iter_admin_modules() -> list[SourceModule]:
    return [
        module
        for module in iter_source_modules()
        if module.source_parts[:1] == ("core",)
        if module.source_parts[-3:] == ("delivery", "django", "admin.py")
    ]


def _iter_admin_paths() -> list[Path]:
    return [module.path for module in _iter_admin_modules()]


def _admin_registrations_by_domain() -> dict[str, set[str]]:
    registrations: dict[str, set[str]] = {}

    for module in _iter_admin_modules():
        domain_registrations = registrations.setdefault(module.source_parts[1], set())
        for class_node in iter_class_definitions(module):
            domain_registrations.update(_registered_model_names(class_node))

    return registrations


def _registered_model_names(class_node: ast.ClassDef) -> set[str]:
    return {
        model_name
        for decorator in class_node.decorator_list
        if isinstance(decorator, ast.Call)
        if name_for_expression(decorator.func) == "register"
        for argument in decorator.args[:1]
        if (model_name := name_for_expression(argument)) is not None
    }


def _domain_apps_imports_admin(admin_path: Path) -> bool:
    domain_root = admin_path.parents[2]
    apps_path = domain_root / "apps.py"

    if not apps_path.exists():
        return False

    module = SourceModule(
        path=apps_path,
        tree=ast.parse(apps_path.read_text(encoding="utf-8"), filename=str(apps_path)),
    )
    expected_module = f"fastdjango.core.{domain_root.name}.delivery.django"

    return any(
        import_reference.module_name == expected_module for import_reference in iter_imports(module)
    )


def _is_concrete_django_model(class_node: ast.ClassDef) -> bool:
    return not class_node.name.startswith("Base") and not base_names(class_node).isdisjoint(
        DJANGO_MODEL_BASE_NAMES,
    )


def _is_model_admin_class(class_node: ast.ClassDef) -> bool:
    return "ModelAdmin" in base_names(class_node)


def _class_assigns_non_empty_sequence(class_node: ast.ClassDef, name: str) -> bool:
    assigned_value = next(
        (
            statement.value
            for statement in class_node.body
            if isinstance(statement, ast.Assign | ast.AnnAssign)
            if _assigned_name(statement) == name
        ),
        None,
    )

    return isinstance(assigned_value, ast.List | ast.Tuple) and bool(assigned_value.elts)


def _assigned_name(statement: ast.stmt) -> str | None:
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return statement.target.id

    if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
        target = statement.targets[0]
        if isinstance(target, ast.Name):
            return target.id

    return None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
