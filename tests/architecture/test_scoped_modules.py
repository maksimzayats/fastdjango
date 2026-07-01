import ast
from collections.abc import Iterable

from tests.architecture._source import REPO_ROOT, SOURCE_ROOT, SourceModule, iter_source_modules

AGGREGATE_SOURCE_FILENAMES = {
    "auth.py",
    "configurators.py",
    "constants.py",
    "controllers.py",
    "dtos.py",
    "entities.py",
    "exceptions.py",
    "factories.py",
    "mappers.py",
    "models.py",
    "repositories.py",
    "schemas.py",
    "services.py",
    "throttling.py",
    "use_cases.py",
}
AUXILIARY_CLASS_SUFFIXES = {
    "Result",
    "Settings",
    "State",
}
MANAGEMENT_ROOT = REPO_ROOT / "management"


def test_source_modules_do_not_use_aggregate_filenames() -> None:
    violations = [
        str(module.relative_path)
        for module in _iter_scoped_modules()
        if module.path.name in AGGREGATE_SOURCE_FILENAMES
    ]

    assert violations == [], "Source files must use scoped singular names, not aggregate names."


def test_source_modules_have_one_primary_public_class() -> None:
    violations = [
        f"{module.relative_path}: {', '.join(primary_class_names)}"
        for module in _iter_scoped_modules()
        if (
            primary_class_names := [
                class_node.name
                for class_node in _public_classes(module=module)
                if not _is_auxiliary_class(class_name=class_node.name)
            ]
        )
        if len(primary_class_names) > 1
    ]

    assert violations == [], "A scoped source file may define only one primary public class."


def test_source_modules_do_not_mix_public_classes_and_functions() -> None:
    violations = [
        f"{module.relative_path}: classes={class_names}; functions={function_names}"
        for module in _iter_scoped_modules()
        if (class_names := [class_node.name for class_node in _public_classes(module=module)])
        if (
            function_names := [
                function_node.name for function_node in _public_functions(module=module)
            ]
        )
    ]

    assert violations == [], "Public functions and public classes must not share one source file."


def test_source_modules_have_at_most_one_public_function() -> None:
    violations = [
        f"{module.relative_path}: {', '.join(function_names)}"
        for module in _iter_scoped_modules()
        if (
            function_names := [
                function_node.name for function_node in _public_functions(module=module)
            ]
        )
        if len(function_names) > 1
    ]

    assert violations == [], "A scoped source file may define only one public function."


def test_source_modules_do_not_use_import_only_public_alias_shims() -> None:
    violations = _import_only_public_alias_shim_violations(modules=_iter_scoped_modules())

    assert violations == [], "Source files must not be import-only public alias shims."


def test_import_only_public_alias_shim_guardrail_rejects_all_exports() -> None:
    module = SourceModule(
        path=SOURCE_ROOT / "core" / "user" / "alias.py",
        tree=ast.parse(
            """
from fastapi_template.core.user.entities.user import User

__all__ = ("User",)
""".lstrip(),
        ),
    )

    assert _import_only_public_alias_shim_violations(modules=[module]) == [
        str(module.relative_path),
    ]


def test_import_only_public_alias_shim_guardrail_rejects_public_import_alias() -> None:
    module = SourceModule(
        path=SOURCE_ROOT / "core" / "user" / "alias.py",
        tree=ast.parse(
            """
import fastapi_template.core.user.entities.user as PublicUser

__all__ = ("PublicUser",)
""".lstrip(),
        ),
    )

    assert _import_only_public_alias_shim_violations(modules=[module]) == [
        str(module.relative_path),
    ]


def test_import_only_public_alias_shim_guardrail_rejects_public_from_import_alias() -> None:
    module = SourceModule(
        path=SOURCE_ROOT / "core" / "user" / "alias.py",
        tree=ast.parse(
            """
from fastapi_template.core.user.entities.user import _PrivateUser as PublicUser

__all__ = ("PublicUser",)
""".lstrip(),
        ),
    )

    assert _import_only_public_alias_shim_violations(modules=[module]) == [
        str(module.relative_path),
    ]


def test_import_only_public_alias_shim_guardrail_rejects_assignment_alias() -> None:
    module = SourceModule(
        path=SOURCE_ROOT / "core" / "user" / "alias.py",
        tree=ast.parse(
            """
from fastapi_template.core.user.entities.user import User as _User

User = _User
__all__ = ("User",)
""".lstrip(),
        ),
    )

    assert _import_only_public_alias_shim_violations(modules=[module]) == [
        str(module.relative_path),
    ]


def _import_only_public_alias_shim_violations(
    *,
    modules: Iterable[SourceModule],
) -> list[str]:
    return [
        str(module.relative_path)
        for module in modules
        if module.path.name != "__init__.py"
        if _has_public_alias_binding(module=module)
        if not _public_classes(module=module)
        if not _public_functions(module=module)
        if _is_import_only_module(module=module)
    ]


def _iter_scoped_modules() -> Iterable[SourceModule]:
    yield from iter_source_modules()
    for source_file in sorted(MANAGEMENT_ROOT.rglob("*.py")):
        yield SourceModule(
            path=source_file,
            tree=ast.parse(
                source_file.read_text(encoding="utf-8"),
                filename=str(source_file),
            ),
        )


def _public_classes(*, module: SourceModule) -> list[ast.ClassDef]:
    return [
        node
        for node in module.tree.body
        if isinstance(node, ast.ClassDef)
        if not node.name.startswith("_")
    ]


def _public_functions(*, module: SourceModule) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node
        for node in module.tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        if not node.name.startswith("_")
    ]


def _is_auxiliary_class(*, class_name: str) -> bool:
    return any(class_name.endswith(suffix) for suffix in AUXILIARY_CLASS_SUFFIXES)


def _has_public_alias_binding(*, module: SourceModule) -> bool:
    import_bindings = _import_binding_names(module=module)
    has_public_import = any(
        not _import_alias_binding_name(alias=alias).startswith("_")
        for node in module.tree.body
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    )
    if has_public_import:
        return True

    return any(
        _is_import_alias_assignment(node=node, import_bindings=import_bindings)
        for node in module.tree.body
    )


def _is_import_only_module(*, module: SourceModule) -> bool:
    import_bindings = _import_binding_names(module=module)
    return all(
        isinstance(node, ast.Import | ast.ImportFrom)
        or _is_all_assignment(node=node)
        or _is_import_alias_assignment(node=node, import_bindings=import_bindings)
        for node in _non_docstring_nodes(module=module)
    )


def _import_binding_names(*, module: SourceModule) -> set[str]:
    return {
        _import_alias_binding_name(alias=alias)
        for node in module.tree.body
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    }


def _is_all_assignment(*, node: ast.stmt) -> bool:
    if isinstance(node, ast.Assign):
        return any(_is_all_target(target=target) for target in node.targets)

    return isinstance(node, ast.AnnAssign) and _is_all_target(target=node.target)


def _is_all_target(*, target: ast.expr) -> bool:
    return isinstance(target, ast.Name) and target.id == "__all__"


def _is_import_alias_assignment(*, node: ast.stmt, import_bindings: set[str]) -> bool:
    if not isinstance(node, ast.Assign | ast.AnnAssign):
        return False

    if not any(not name.startswith("_") for name in _assignment_target_names(node=node)):
        return False

    return isinstance(node.value, ast.Name) and node.value.id in import_bindings


def _assignment_target_names(*, node: ast.Assign | ast.AnnAssign) -> list[str]:
    if isinstance(node, ast.Assign):
        return [target.id for target in node.targets if isinstance(target, ast.Name)]

    if isinstance(node.target, ast.Name):
        return [node.target.id]

    return []


def _import_alias_binding_name(*, alias: ast.alias) -> str:
    if alias.asname is not None:
        return alias.asname

    return alias.name.split(".", maxsplit=1)[0]


def _non_docstring_nodes(*, module: SourceModule) -> list[ast.stmt]:
    return [
        node
        for index, node in enumerate(module.tree.body)
        if not (
            index == 0
            and isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
    ]
