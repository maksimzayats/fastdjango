from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "fastdjango"
TESTS_ROOT = REPO_ROOT / "tests"

MIRRORED_TEST_LAYER_NAMES = ("integration", "unit")


def test_mirrored_test_files_map_to_source_modules() -> None:
    missing_source_modules: list[str] = []

    for test_file in _iter_mirrored_test_files():
        source_path = SOURCE_ROOT / _source_module_path_for(test_file)
        if not source_path.is_file():
            missing_source_modules.append(
                f"{test_file.relative_to(REPO_ROOT)} -> {source_path.relative_to(REPO_ROOT)}",
            )

    assert missing_source_modules == [], (
        "Mirrored unit and integration test files must map to source modules. "
        "Keep test paths aligned with the source module they cover."
    )


def test_important_source_modules_have_matching_tests() -> None:
    missing_tests = [
        f"{source_path.relative_to(REPO_ROOT)} -> {test_path.relative_to(REPO_ROOT)}"
        for source_path in _iter_important_source_modules()
        for test_path in [_expected_test_path_for(source_path)]
        if not test_path.is_file()
    ]

    assert missing_tests == [], (
        "Important behavior modules must have matching tests. "
        "Cover delivery controllers/tasks with integration tests and "
        "services/use cases with unit tests."
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

    source_modules.extend(sorted(SOURCE_ROOT.glob("core/*/delivery/fastapi/controllers.py")))
    source_modules.extend(sorted(SOURCE_ROOT.glob("core/*/delivery/celery/tasks.py")))
    source_modules.extend(
        source_path
        for source_path in sorted(SOURCE_ROOT.glob("core/*/services/*.py"))
        if source_path.name != "__init__.py"
    )
    source_modules.extend(sorted(SOURCE_ROOT.glob("core/*/use_cases.py")))

    return source_modules


def _expected_test_path_for(source_path: Path) -> Path:
    source_relative_path = source_path.relative_to(SOURCE_ROOT)

    if "delivery" in source_relative_path.parts:
        return TESTS_ROOT / "integration" / _test_module_path_for(source_relative_path)

    return TESTS_ROOT / "unit" / _test_module_path_for(source_relative_path)


def _test_module_path_for(source_relative_path: Path) -> Path:
    return source_relative_path.with_name(f"test_{source_relative_path.name}")
