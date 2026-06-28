import ast

from tests.architecture._source import SourceModule, iter_source_modules

AGGREGATE_SOURCE_FILENAMES = {
    "auth.py",
    "configurators.py",
    "controllers.py",
    "dtos.py",
    "exceptions.py",
    "factories.py",
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


def test_source_modules_do_not_use_aggregate_filenames() -> None:
    violations = [
        str(module.relative_path)
        for module in iter_source_modules()
        if module.path.name in AGGREGATE_SOURCE_FILENAMES
    ]

    assert violations == [], "Source files must use scoped singular names, not aggregate names."


def test_source_modules_have_one_primary_public_class() -> None:
    violations = [
        f"{module.relative_path}: {', '.join(primary_class_names)}"
        for module in iter_source_modules()
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
        for module in iter_source_modules()
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
        for module in iter_source_modules()
        if (
            function_names := [
                function_node.name for function_node in _public_functions(module=module)
            ]
        )
        if len(function_names) > 1
    ]

    assert violations == [], "A scoped source file may define only one public function."


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
