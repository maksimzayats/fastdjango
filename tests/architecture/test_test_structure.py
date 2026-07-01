import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "fastapi_template"
TESTS_ROOT = REPO_ROOT / "tests"

MIRRORED_TEST_LAYER_NAMES = ("integration", "unit")
AGGREGATE_TEST_FILENAMES = {
    "test_auth.py",
    "test_controllers.py",
    "test_entities.py",
    "test_factories.py",
    "test_mappers.py",
    "test_repositories.py",
    "test_services.py",
    "test_throttler.py",
    "test_use_cases.py",
}
DIRECT_INTEGRATION_FACTORY_NAMES = frozenset(
    (
        "TestClientFactory",
        "TestRefreshSessionFactory",
        "TestUserFactory",
    ),
)


def test_mirrored_test_files_map_to_source_modules() -> None:
    missing_source_modules: list[str] = []

    for test_file in _iter_mirrored_test_files():
        source_path = SOURCE_ROOT / _source_module_path_for(test_file)
        if not source_path.exists():
            missing_source_modules.append(
                f"{test_file.relative_to(REPO_ROOT)} -> {source_path.relative_to(REPO_ROOT)}",
            )

    assert missing_source_modules == [], (
        "Mirrored unit and integration test files must map to source modules. "
        "Keep test paths aligned with the source module they cover."
    )


def test_important_source_modules_have_matching_tests() -> None:
    missing_tests: list[str] = []
    for source_path in _iter_important_source_modules():
        expected_paths = _expected_test_paths_for(source_path)
        if not any(test_path.is_file() for test_path in expected_paths):
            missing_tests.append(
                f"{source_path.relative_to(REPO_ROOT)} -> "
                f"{', '.join(str(path.relative_to(REPO_ROOT)) for path in expected_paths)}",
            )

    assert missing_tests == [], (
        "Important behavior modules must have matching tests. "
        "Cover delivery controllers with integration tests and services/use cases with unit tests."
    )


def test_sqlalchemy_repository_tests_mirror_concrete_adapters() -> None:
    stale_repository_tests = [
        str(path.relative_to(REPO_ROOT))
        for path in sorted((TESTS_ROOT / "integration").rglob("test_repositories.py"))
    ]

    assert stale_repository_tests == [], (
        "SQLAlchemy repository integration tests must mirror the concrete adapter path under "
        "tests/integration/core/<domain>/infrastructure/sqlalchemy/."
    )


def test_mirrored_tests_do_not_use_aggregate_filenames() -> None:
    aggregate_tests = [
        str(path.relative_to(REPO_ROOT))
        for path in _iter_mirrored_test_files()
        if path.name in AGGREGATE_TEST_FILENAMES
    ]

    assert aggregate_tests == [], "Mirrored tests must target concrete scoped source modules."


def test_integration_tests_do_not_use_persistence_nesting() -> None:
    """Ensure integration tests mirror the flat local SQLAlchemy adapter path."""
    persistence_paths = [
        path.relative_to(REPO_ROOT)
        for path in sorted(
            (TESTS_ROOT / "integration" / "core").glob("*/infrastructure/persistence"),
        )
    ]

    assert persistence_paths == []


def test_delivery_integration_tests_use_factory_fixtures() -> None:
    direct_factory_calls = [
        f"{path.relative_to(REPO_ROOT)}:{node.lineno} calls {call_name}"
        for path, tree in _iter_delivery_integration_modules()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        if (call_name := _call_name(node)) in DIRECT_INTEGRATION_FACTORY_NAMES
    ]

    assert direct_factory_calls == [], (
        "Delivery integration tests must use factory fixtures from tests/integration/conftest.py."
    )


def test_delivery_integration_tests_do_not_import_sqlalchemy_boundaries() -> None:
    forbidden_imports = [
        f"{path.relative_to(REPO_ROOT)}:{line_number} imports {module_name}"
        for path, tree in _iter_delivery_integration_modules()
        for module_name, line_number in _iter_imports(tree=tree)
        if _is_delivery_integration_sqlalchemy_import(module_name=module_name)
    ]

    assert forbidden_imports == [], (
        "Delivery integration tests must prepare database state through UoW-backed "
        "fixtures and factories, not SQLAlchemy models, sessions, or adapters."
    )


def test_delivery_integration_tests_do_not_resolve_container_dependencies() -> None:
    container_resolves = [
        f"{path.relative_to(REPO_ROOT)}:{node.lineno} calls container.resolve()"
        for path, tree in _iter_delivery_integration_modules()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        if _is_container_resolve_call(node=node)
    ]

    assert container_resolves == [], (
        "Delivery integration tests must override dependencies before client creation "
        "and use shared factories instead of resolving the container directly."
    )


def _iter_mirrored_test_files() -> list[Path]:
    test_files: list[Path] = []

    for layer_name in MIRRORED_TEST_LAYER_NAMES:
        layer_root = TESTS_ROOT / layer_name
        test_files.extend(sorted(layer_root.rglob("test_*.py")))

    return test_files


def _source_module_path_for(test_file: Path) -> Path:
    test_path = test_file.relative_to(TESTS_ROOT)
    _, *source_parts = test_path.parts
    source_module_name = source_parts[-1].removeprefix("test_")
    return Path(*source_parts[:-1], source_module_name)


def _iter_important_source_modules() -> list[Path]:
    source_modules: list[Path] = []

    source_modules.extend(
        source_path
        for source_path in sorted(SOURCE_ROOT.glob("core/*/delivery/fastapi/controllers/*.py"))
        if source_path.name != "__init__.py"
    )
    source_modules.extend(
        source_path
        for source_path in sorted(
            SOURCE_ROOT.glob("core/*/infrastructure/sqlalchemy/repositories/*.py"),
        )
        if source_path.name != "__init__.py"
    )
    source_modules.extend(
        source_path
        for source_path in sorted(SOURCE_ROOT.glob("core/*/services/*.py"))
        if source_path.name != "__init__.py"
    )
    source_modules.extend(
        source_path
        for source_path in sorted(SOURCE_ROOT.glob("core/*/use_cases/*.py"))
        if source_path.name != "__init__.py"
    )

    return source_modules


def _expected_test_paths_for(source_path: Path) -> tuple[Path, ...]:
    source_relative_path = source_path.relative_to(SOURCE_ROOT)

    if "delivery" in source_relative_path.parts or _is_local_sqlalchemy_adapter(
        source_relative_path,
    ):
        test_root = TESTS_ROOT / "integration"
    else:
        test_root = TESTS_ROOT / "unit"

    return (test_root / _test_module_path_for(source_relative_path),)


def _is_local_sqlalchemy_adapter(source_relative_path: Path) -> bool:
    return (
        "infrastructure" in source_relative_path.parts
        and "sqlalchemy" in source_relative_path.parts
    )


def _test_module_path_for(source_relative_path: Path) -> Path:
    return source_relative_path.with_name(f"test_{source_relative_path.name}")


def _iter_delivery_integration_modules() -> list[tuple[Path, ast.Module]]:
    delivery_root = TESTS_ROOT / "integration" / "core"

    return [
        (
            path,
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path)),
        )
        for path in sorted(delivery_root.glob("*/delivery/**/*.py"))
        if path.name != "__init__.py"
    ]


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        return node.func.attr

    return None


def _iter_imports(*, tree: ast.Module) -> list[tuple[str, int]]:
    imports: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((alias.name, node.lineno) for alias in node.names)
            continue

        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append((node.module, node.lineno))

    return imports


def _is_delivery_integration_sqlalchemy_import(*, module_name: str) -> bool:
    if module_name.startswith("sqlalchemy"):
        return True

    if module_name.startswith("fastapi_template.infrastructure.sqlalchemy"):
        return True

    return (
        module_name.startswith("fastapi_template.core.")
        and ".infrastructure.sqlalchemy" in module_name
    )


def _is_container_resolve_call(*, node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Attribute)
        and node.func.attr == "resolve"
        and (receiver_name := _expression_name(node.func.value)) is not None
        and receiver_name.endswith("container")
    )


def _expression_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return None
