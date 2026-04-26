import ast
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "fastdjango"
TESTS_ROOT = REPO_ROOT / "tests"


@dataclass(frozen=True)
class SourceModule:
    path: Path
    tree: ast.Module

    @property
    def relative_path(self) -> Path:
        return self.path.relative_to(REPO_ROOT)

    @property
    def source_parts(self) -> tuple[str, ...]:
        return self.path.relative_to(SOURCE_ROOT).parts

    @property
    def module_name(self) -> str:
        module_path = self.path.relative_to(SOURCE_ROOT).with_suffix("")
        return f"fastdjango.{'.'.join(module_path.parts)}"


@dataclass(frozen=True)
class ImportReference:
    module_name: str
    line_number: int
    is_type_checking: bool = False


def iter_source_modules() -> Iterable[SourceModule]:
    for source_file in sorted(SOURCE_ROOT.rglob("*.py")):
        yield SourceModule(
            path=source_file,
            tree=ast.parse(
                source_file.read_text(encoding="utf-8"),
                filename=str(source_file),
            ),
        )


def iter_class_definitions(module: SourceModule) -> Iterable[ast.ClassDef]:
    return (node for node in ast.walk(module.tree) if isinstance(node, ast.ClassDef))


def iter_imports(module: SourceModule) -> Iterable[ImportReference]:
    yield from _iter_imports(module.tree, is_type_checking=False)


def base_names(class_node: ast.ClassDef) -> set[str]:
    return {
        base_name
        for base in class_node.bases
        if (base_name := name_for_expression(_unwrap_subscript(base))) is not None
    }


def has_base(class_node: ast.ClassDef, bases: set[str]) -> bool:
    return not base_names(class_node).isdisjoint(bases)


def has_dataclass_kw_only_decorator(class_node: ast.ClassDef) -> bool:
    for decorator in class_node.decorator_list:
        if isinstance(decorator, ast.Call) and name_for_expression(decorator.func) == "dataclass":
            return any(
                keyword.arg == "kw_only"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in decorator.keywords
            )

    return False


def is_classvar_annotation(annotation: ast.expr) -> bool:
    annotation_target = annotation.value if isinstance(annotation, ast.Subscript) else annotation
    return name_for_expression(annotation_target) == "ClassVar"


def is_injected_annotation(annotation: ast.expr) -> bool:
    return (
        isinstance(annotation, ast.Subscript)
        and name_for_expression(annotation.value) == "Injected"
    )


def name_for_expression(expression: ast.expr) -> str | None:
    if isinstance(expression, ast.Name):
        return expression.id

    if isinstance(expression, ast.Attribute):
        return expression.attr

    return None


def _unwrap_subscript(expression: ast.expr) -> ast.expr:
    if isinstance(expression, ast.Subscript):
        return expression.value

    return expression


def _iter_imports(
    node: ast.AST,
    *,
    is_type_checking: bool,
) -> Iterable[ImportReference]:
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        yield ImportReference(
            module_name=node.module,
            line_number=node.lineno,
            is_type_checking=is_type_checking,
        )
        return

    if isinstance(node, ast.Import):
        for alias in node.names:
            yield ImportReference(
                module_name=alias.name,
                line_number=node.lineno,
                is_type_checking=is_type_checking,
            )
        return

    if isinstance(node, ast.If):
        next_is_type_checking = is_type_checking or _is_type_checking_test(node.test)
        for child in node.body:
            yield from _iter_imports(child, is_type_checking=next_is_type_checking)
        for child in node.orelse:
            yield from _iter_imports(child, is_type_checking=is_type_checking)
        return

    for child_node in ast.iter_child_nodes(node):
        yield from _iter_imports(child_node, is_type_checking=is_type_checking)


def _is_type_checking_test(expression: ast.expr) -> bool:
    return (isinstance(expression, ast.Name) and expression.id == "TYPE_CHECKING") or (
        isinstance(expression, ast.Attribute) and expression.attr == "TYPE_CHECKING"
    )
