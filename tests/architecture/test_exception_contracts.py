import ast
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "fastdjango"

SERVICE_AND_USE_CASE_BASES = {"BaseService", "BaseUseCase"}
EXCEPTION_NAME_SUFFIXES = ("Error", "Exception", "_ERROR", "_EXCEPTION")
EXCEPTION_ALIAS_NAMES = {"DoesNotExist"}


def test_service_and_use_case_exceptions_are_classvar_contracts() -> None:
    violations = [
        violation
        for source_file, tree in _iter_source_trees()
        for class_node in _iter_service_and_use_case_classes(tree)
        for violation in _exception_contract_violations(
            source_file=source_file,
            class_node=class_node,
        )
    ]

    assert violations == [], (
        "Services and use cases must expose raised/caught exception classes as "
        "ClassVar contracts and use those contracts in raise/except statements."
    )


def test_delivery_modules_handle_domain_exceptions_through_contracts() -> None:
    violations = [
        f"{_relative_path(source_file)}:{node.lineno} imports {node.module}"
        for source_file, tree in _iter_delivery_source_trees()
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and _is_domain_exception_module(node.module)
    ]

    assert violations == [], (
        "Delivery modules must handle domain exceptions through injected service "
        "or use-case exception contracts instead of importing domain exception modules."
    )


def _exception_contract_violations(
    *,
    source_file: Path,
    class_node: ast.ClassDef,
) -> list[str]:
    classvar_names = _classvar_names(class_node)
    violations = _unannotated_exception_alias_violations(
        source_file=source_file,
        class_node=class_node,
        classvar_names=classvar_names,
    )
    violations.extend(
        _direct_raise_or_except_violations(
            source_file=source_file,
            class_node=class_node,
            classvar_names=classvar_names,
        ),
    )
    return violations


def _unannotated_exception_alias_violations(
    *,
    source_file: Path,
    class_node: ast.ClassDef,
    classvar_names: set[str],
) -> list[str]:
    return [
        (
            f"{_relative_path(source_file)}:{line_number} "
            f"{class_node.name}.{name} must be annotated with ClassVar"
        )
        for name, line_number in _exception_aliases(class_node).items()
        if name not in classvar_names
    ]


def _direct_raise_or_except_violations(
    *,
    source_file: Path,
    class_node: ast.ClassDef,
    classvar_names: set[str],
) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(class_node):
        if isinstance(node, ast.Raise):
            violations.extend(
                _raise_violations(
                    source_file=source_file,
                    class_node=class_node,
                    classvar_names=classvar_names,
                    node=node,
                ),
            )
        if isinstance(node, ast.ExceptHandler):
            violations.extend(
                _except_violations(
                    source_file=source_file,
                    class_node=class_node,
                    classvar_names=classvar_names,
                    node=node,
                ),
            )

    return violations


def _raise_violations(
    *,
    source_file: Path,
    class_node: ast.ClassDef,
    classvar_names: set[str],
    node: ast.Raise,
) -> list[str]:
    if node.exc is None or _is_exception_contract_reference(
        node.exc,
        class_name=class_node.name,
        classvar_names=classvar_names,
    ):
        return []

    if not _looks_like_exception_reference(node.exc):
        return []

    return [
        (
            f"{_relative_path(source_file)}:{node.lineno} {class_node.name} "
            f"raises {ast.unparse(node.exc)} directly"
        ),
    ]


def _except_violations(
    *,
    source_file: Path,
    class_node: ast.ClassDef,
    classvar_names: set[str],
    node: ast.ExceptHandler,
) -> list[str]:
    return [
        (
            f"{_relative_path(source_file)}:{node.lineno} {class_node.name} "
            f"catches {ast.unparse(exception_type)} directly"
        )
        for exception_type in _iter_exception_types(node.type)
        if not _is_exception_contract_reference(
            exception_type,
            class_name=class_node.name,
            classvar_names=classvar_names,
        )
        and _looks_like_exception_reference(exception_type)
    ]


def _iter_source_trees() -> Iterable[tuple[Path, ast.Module]]:
    for source_file in sorted(SOURCE_ROOT.rglob("*.py")):
        yield (
            source_file,
            ast.parse(
                source_file.read_text(encoding="utf-8"),
                filename=str(source_file),
            ),
        )


def _iter_delivery_source_trees() -> Iterable[tuple[Path, ast.Module]]:
    for source_file, tree in _iter_source_trees():
        if "delivery" in source_file.relative_to(SOURCE_ROOT).parts:
            yield source_file, tree


def _iter_service_and_use_case_classes(tree: ast.Module) -> Iterable[ast.ClassDef]:
    return (
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and _has_service_or_use_case_base(node)
    )


def _has_service_or_use_case_base(class_node: ast.ClassDef) -> bool:
    return any(
        _name_for_expression(base) in SERVICE_AND_USE_CASE_BASES for base in class_node.bases
    )


def _classvar_names(class_node: ast.ClassDef) -> set[str]:
    return {
        target.id
        for statement in class_node.body
        if isinstance(statement, ast.AnnAssign)
        if isinstance(statement.target, ast.Name)
        if _is_classvar_annotation(statement.annotation)
        for target in [statement.target]
    }


def _exception_aliases(class_node: ast.ClassDef) -> dict[str, int]:
    aliases: dict[str, int] = {}
    for statement in class_node.body:
        value = _assignment_value(statement)
        if value is None or not _looks_like_exception_reference(value):
            continue

        aliases.update(
            dict.fromkeys(
                _assignment_target_names(statement),
                statement.lineno,
            ),
        )

    return aliases


def _assignment_value(statement: ast.stmt) -> ast.expr | None:
    if isinstance(statement, ast.Assign):
        return statement.value

    if isinstance(statement, ast.AnnAssign):
        return statement.value

    return None


def _assignment_target_names(statement: ast.stmt) -> Iterable[str]:
    if isinstance(statement, ast.Assign):
        return (target.id for target in statement.targets if isinstance(target, ast.Name))

    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return (statement.target.id,)

    return ()


def _is_classvar_annotation(annotation: ast.expr) -> bool:
    annotation_target = annotation.value if isinstance(annotation, ast.Subscript) else annotation
    return _name_for_expression(annotation_target) == "ClassVar"


def _is_exception_contract_reference(
    expression: ast.expr,
    *,
    class_name: str,
    classvar_names: set[str],
) -> bool:
    expression = _call_target(expression)
    return (
        _is_self_contract_reference(expression, classvar_names=classvar_names)
        or _is_class_contract_reference(
            expression,
            class_name=class_name,
            classvar_names=classvar_names,
        )
        or _name_for_expression(expression) in classvar_names
    )


def _is_self_contract_reference(
    expression: ast.expr,
    *,
    classvar_names: set[str],
) -> bool:
    return (
        isinstance(expression, ast.Attribute)
        and isinstance(expression.value, ast.Name)
        and expression.value.id == "self"
        and expression.attr in classvar_names
    )


def _is_class_contract_reference(
    expression: ast.expr,
    *,
    class_name: str,
    classvar_names: set[str],
) -> bool:
    return (
        isinstance(expression, ast.Attribute)
        and isinstance(expression.value, ast.Name)
        and expression.value.id == class_name
        and expression.attr in classvar_names
    )


def _looks_like_exception_reference(expression: ast.expr) -> bool:
    expression = _call_target(expression)
    if isinstance(expression, ast.Tuple):
        return any(_looks_like_exception_reference(element) for element in expression.elts)

    expression_name = _name_for_expression(expression)
    return expression_name is not None and _is_exception_name(expression_name)


def _iter_exception_types(expression: ast.expr | None) -> Iterable[ast.expr]:
    if expression is None:
        return ()

    if isinstance(expression, ast.Tuple):
        return tuple(expression.elts)

    return (expression,)


def _call_target(expression: ast.expr) -> ast.expr:
    if isinstance(expression, ast.Call):
        return expression.func

    return expression


def _name_for_expression(expression: ast.expr) -> str | None:
    if isinstance(expression, ast.Name):
        return expression.id

    if isinstance(expression, ast.Attribute):
        return expression.attr

    return None


def _is_exception_name(name: str) -> bool:
    return name.endswith(EXCEPTION_NAME_SUFFIXES) or name in EXCEPTION_ALIAS_NAMES


def _is_domain_exception_module(module_name: str) -> bool:
    return module_name.startswith("fastdjango.core.") and module_name.endswith(".exceptions")


def _relative_path(path: Path) -> Path:
    return path.relative_to(REPO_ROOT)
