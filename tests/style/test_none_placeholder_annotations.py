import ast
from collections.abc import Iterable
from pathlib import Path

from tests.architecture._source import REPO_ROOT, SOURCE_ROOT, TESTS_ROOT


def test_local_none_placeholders_are_annotated() -> None:
    violations = [
        f"{path.relative_to(REPO_ROOT)}:{node.lineno} {target.id} = None"
        for path, tree in _iter_project_python_trees()
        for function_node in ast.walk(tree)
        if isinstance(function_node, ast.FunctionDef | ast.AsyncFunctionDef)
        for node in _iter_own_function_body(function_node)
        if isinstance(node, ast.Assign)
        if _is_none_constant(node.value)
        for target in node.targets
        if isinstance(target, ast.Name)
    ]

    assert violations == [], (
        "Local placeholders initialized to None must use an explicit annotation, "
        "for example `result: ResultType | None = None`."
    )


def _iter_project_python_trees() -> Iterable[tuple[Path, ast.Module]]:
    for root in (SOURCE_ROOT, TESTS_ROOT):
        for path in sorted(root.rglob("*.py")):
            yield path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _iter_own_function_body(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> Iterable[ast.AST]:
    for statement in function_node.body:
        yield from _walk_without_nested_functions(statement)


def _walk_without_nested_functions(node: ast.AST) -> Iterable[ast.AST]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return

    yield node

    for child in ast.iter_child_nodes(node):
        yield from _walk_without_nested_functions(child)


def _is_none_constant(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is None
