from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "fastapi_template"
TESTS_ROOT = REPO_ROOT / "tests"

MIRRORED_TEST_LAYER_NAMES = ("integration", "unit")
AGGREGATE_TEST_FILENAMES = {
    "test_auth.py",
    "test_controllers.py",
    "test_factories.py",
    "test_repositories.py",
    "test_services.py",
    "test_throttler.py",
    "test_use_cases.py",
}


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
