import ast
import configparser
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from tests.architecture._source import REPO_ROOT
from tests.integration.conftest import validate_integration_database_url

SOURCE_ROOT = REPO_ROOT / "src" / "fastapi_template"
QUALITY_HOOK_NAMES = {
    "mypy",
    "ruff check",
    "ruff format check",
    "wemake-python-styleguide",
}
FOCUSED_REPOSITORY_HOOK_IDS = {
    "actionlint",
    "check-compose-spec",
    "check-dependabot",
    "check-github-actions",
    "check-github-workflows",
    "codespell",
    "zizmor",
}
WORKFLOWS_WITH_CONTENT_WRITE_PERMISSIONS: set[str] = set()
REMOVED_PROJECT_CUSTOMIZER_MODULE = "setup_" + "wiz" + "ard"
REMOVED_PROJECT_CUSTOMIZER_PATHS = {
    REPO_ROOT / "management" / REMOVED_PROJECT_CUSTOMIZER_MODULE,
    REPO_ROOT / "tests" / REMOVED_PROJECT_CUSTOMIZER_MODULE,
}
REMOVED_PROJECT_CUSTOMIZER_MARKERS = {
    f"management/{REMOVED_PROJECT_CUSTOMIZER_MODULE}",
    f"tests/{REMOVED_PROJECT_CUSTOMIZER_MODULE}",
    "--group " + "setup",
}
STALE_DOCUMENTATION_MARKERS = {
    "backward " + "compat",
    "backward-" + "compatible",
    "backwards " + "compat",
    "cel" + "ery",
    "compat " + "shim",
    "compatibility " + "shim",
    "djan" + "go",
    "fl" + "ask",
    "min" + "io",
    "old " + "stack",
    "old-" + "stack",
    "scr" + "apy",
    "setup " + "wizard",
    "setup_" + "wizard",
}
EXCEPTION_CONTRACT_SUFFIXES = ("_ERROR", "_EXCEPTION")


def test_prek_quality_hooks_run_against_the_whole_project() -> None:
    hooks = _prek_hooks_by_name()
    violations = [
        hook_name
        for hook_name in sorted(QUALITY_HOOK_NAMES)
        if not _is_whole_project_hook(hooks.get(hook_name))
    ]

    assert violations == [], (
        "Quality hooks must run whole-project checks with pass_filenames=false "
        "so architecture changes are not missed by staged-file filtering."
    )


def test_mypy_hook_uses_test_environment_file() -> None:
    mypy_hook = _prek_hooks_by_name()["mypy"]

    assert "--env-file .env.test.example" in mypy_hook["entry"]


def test_focused_repository_quality_hooks_are_enabled() -> None:
    hooks = _prek_hooks_by_id()

    assert FOCUSED_REPOSITORY_HOOK_IDS.issubset(hooks.keys())


def test_ruff_config_keeps_broad_rule_selection_and_safe_preview() -> None:
    ruff_config = _read_toml(REPO_ROOT / "ruff.toml")
    lint_config = cast(dict[str, Any], ruff_config["lint"])
    ruff_lint_config = cast(dict[str, Any], lint_config["ruff"])
    tidy_imports_config = cast(dict[str, Any], lint_config["flake8-tidy-imports"])

    assert lint_config["select"] == ["ALL"]
    assert lint_config["external"] == ["WPS"]
    assert lint_config["preview"] is True
    assert lint_config["explicit-preview-rules"] is True
    assert ruff_lint_config["strictly-empty-init-modules"] is True
    assert tidy_imports_config["ban-relative-imports"] == "all"


def test_wemake_styleguide_config_is_strict_but_scoped() -> None:
    config = configparser.ConfigParser()
    config.read(REPO_ROOT / "setup.cfg", encoding="utf-8")
    flake8_config = config["flake8"]

    assert flake8_config["format"] == "wemake"
    assert flake8_config["select"] == "WPS,E999"
    assert flake8_config["max-complexity"] == "6"
    assert flake8_config["max-imports"] == "17"
    assert flake8_config["max-arguments"] == "6"
    assert "tests" not in _normalized_words(flake8_config["per-file-ignores"])
    assert not any(code == "WPS" for code in _wps_ignore_codes(flake8_config["per-file-ignores"]))
    assert _wildcard_wps_ignores(value=flake8_config["per-file-ignores"]) == {}


def test_wemake_wildcard_ignore_check_rejects_wps115() -> None:
    value = """
src/fastapi_template/core/**/repositories/*.py:
  WPS115
""".strip()

    assert _wildcard_wps_ignores(value=value) != {}


def test_wps115_suppressions_only_mark_exception_contracts() -> None:
    violations = [
        f"{path.relative_to(REPO_ROOT)}:{line_number} contains WPS115"
        for path in sorted(SOURCE_ROOT.rglob("*.py"))
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if "WPS115" in line
        if line_number not in _exception_contract_line_numbers(path=path)
    ]

    assert violations == [], "WPS115 suppressions must stay on exception contract ClassVars."


def test_wps115_suppression_check_rejects_non_contracts(tmp_path: Path) -> None:
    source_file = tmp_path / "example.py"
    source_file.write_text("class Example:\n    SETTING = 1  # noqa: WPS115\n", encoding="utf-8")

    assert _exception_contract_line_numbers(path=source_file) == set()


def test_makefile_quality_targets_use_prek() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    format_recipe = _make_target_recipe(makefile=makefile, target="format")
    lint_recipe = _make_target_recipe(makefile=makefile, target="lint")

    assert any(command.startswith("uv run prek run") for command in format_recipe)
    assert "uv run prek run --all-files" in lint_recipe


@pytest.mark.parametrize(
    "database_url",
    [
        "postgres://postgres:password@localhost:5432/test_modern_python_template",
        "postgresql://postgres:password@localhost:5432/modern_python_template_test",
    ],
)
def test_integration_database_url_guard_accepts_test_database_names(
    database_url: str,
) -> None:
    validate_integration_database_url(database_url=database_url)


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///tmp/test.sqlite3",
        "postgres://postgres:password@localhost:5432/modern_python_template",
    ],
)
def test_integration_database_url_guard_rejects_unsafe_targets(database_url: str) -> None:
    with pytest.raises(pytest.fail.Exception):
        validate_integration_database_url(database_url=database_url)


def test_removed_project_customizer_tooling_surface_stays_removed() -> None:
    pyproject = _read_toml(REPO_ROOT / "pyproject.toml")
    dependency_groups = cast(dict[str, Any], pyproject["dependency-groups"])
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    checked_text = "\n".join(
        [
            makefile,
            (REPO_ROOT / "setup.cfg").read_text(encoding="utf-8"),
            (REPO_ROOT / "prek.toml").read_text(encoding="utf-8"),
        ],
    )

    assert "setup" not in dependency_groups
    assert _make_target_recipe(makefile=makefile, target="setup") == []
    assert not any(path.exists() for path in REMOVED_PROJECT_CUSTOMIZER_PATHS)
    assert not any(marker in checked_text for marker in REMOVED_PROJECT_CUSTOMIZER_MARKERS)


def test_removed_stack_terms_stay_out_of_docs_and_instructions() -> None:
    violations = [
        f"{path.relative_to(REPO_ROOT)} contains {marker!r}"
        for path in _documentation_scan_paths()
        for marker in STALE_DOCUMENTATION_MARKERS
        if marker in path.read_text(encoding="utf-8").lower()
    ]

    assert violations == [], "Docs and agent instructions must not mention removed stack terms."


def test_ci_workflows_use_content_write_permissions_only_when_needed() -> None:
    violations = [
        path.name
        for path in sorted((REPO_ROOT / ".github" / "workflows").glob("*.yaml"))
        if path.name not in WORKFLOWS_WITH_CONTENT_WRITE_PERMISSIONS
        if _workflow_requests_content_write_permissions(path=path)
    ]

    assert violations == [], (
        "Only workflows that change repository contents should request contents: write."
    )


def test_workflow_permission_check_finds_nested_content_write_permissions(
    tmp_path: Path,
) -> None:
    workflow_path = tmp_path / "workflow.yaml"
    workflow_path.write_text(
        """
jobs:
  check:
    permissions:
      contents: write
""".lstrip(),
        encoding="utf-8",
    )

    assert _workflow_requests_content_write_permissions(path=workflow_path)


def _prek_hooks_by_name() -> dict[str, dict[str, Any]]:
    prek_config = _read_toml(REPO_ROOT / "prek.toml")
    repos = cast(list[dict[str, Any]], prek_config["repos"])
    return {
        hook["name"]: hook
        for repo in repos
        for hook in cast(list[dict[str, Any]], repo.get("hooks", []))
        if "name" in hook
    }


def _prek_hooks_by_id() -> dict[str, dict[str, Any]]:
    prek_config = _read_toml(REPO_ROOT / "prek.toml")
    repos = cast(list[dict[str, Any]], prek_config["repos"])
    return {
        hook["id"]: hook
        for repo in repos
        for hook in cast(list[dict[str, Any]], repo.get("hooks", []))
        if "id" in hook
    }


def _is_whole_project_hook(hook: dict[str, Any] | None) -> bool:
    return hook is not None and hook.get("pass_filenames") is False


def _make_target_recipe(*, makefile: str, target: str) -> list[str]:
    lines = makefile.splitlines()
    target_header = f"{target}:"

    for line_index, line in enumerate(lines):
        if line != target_header:
            continue

        recipe: list[str] = []
        for recipe_line in lines[line_index + 1 :]:
            if not recipe_line:
                continue
            if not recipe_line.startswith("\t"):
                break
            recipe.append(recipe_line.strip())

        return recipe

    return []


def _read_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _documentation_scan_paths() -> tuple[Path, ...]:
    return (
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / ".gitignore",
        REPO_ROOT / "README.md",
        *sorted((REPO_ROOT / "docs").rglob("*.md")),
    )


def _normalized_words(value: str) -> set[str]:
    return {word.strip() for word in value.replace(",", " ").split() if word.strip()}


def _wps_ignore_codes(value: str) -> set[str]:
    return {
        word.strip() for word in value.replace(",", " ").split() if word.strip().startswith("WPS")
    }


def _wildcard_wps_ignores(*, value: str) -> dict[str, set[str]]:
    wildcard_ignores: dict[str, set[str]] = {}
    active_path = ""
    for line in value.splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue
        if stripped_line.endswith(":"):
            active_path = stripped_line.removesuffix(":")
            continue
        if "*" in active_path:
            codes = {
                word.strip().removesuffix(",")
                for word in stripped_line.replace(",", " ").split()
                if word.strip().startswith("WPS")
            }
            if codes:
                wildcard_ignores.setdefault(active_path, set()).update(codes)

    return wildcard_ignores


def _exception_contract_line_numbers(*, path: Path) -> set[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        statement.lineno
        for class_node in ast.walk(tree)
        if isinstance(class_node, ast.ClassDef)
        for statement in class_node.body
        if isinstance(statement, ast.AnnAssign)
        if isinstance(statement.target, ast.Name)
        if statement.target.id.endswith(EXCEPTION_CONTRACT_SUFFIXES)
        if _is_classvar_annotation(statement.annotation)
    }


def _is_classvar_annotation(annotation: ast.expr) -> bool:
    if isinstance(annotation, ast.Name):
        return annotation.id == "ClassVar"

    if isinstance(annotation, ast.Subscript) and isinstance(annotation.value, ast.Name):
        return annotation.value.id == "ClassVar"

    return False


def _workflow_requests_content_write_permissions(*, path: Path) -> bool:
    workflow = cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    return _contains_content_write_permissions(node=workflow)


def _contains_content_write_permissions(*, node: object) -> bool:
    if isinstance(node, Mapping):
        permissions = node.get("permissions")
        if permissions == "write-all":
            return True
        if isinstance(permissions, Mapping) and permissions.get("contents") == "write":
            return True

        return any(_contains_content_write_permissions(node=value) for value in node.values())

    if isinstance(node, list):
        return any(_contains_content_write_permissions(node=value) for value in node)

    return False
