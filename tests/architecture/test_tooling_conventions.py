import tomllib
from pathlib import Path
from typing import Any, cast

from tests.architecture._source import REPO_ROOT

QUALITY_HOOK_NAMES = {
    "mypy",
    "ruff check",
    "ruff format check",
}


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


def test_ruff_config_keeps_broad_rule_selection_and_safe_preview() -> None:
    ruff_config = _read_toml(REPO_ROOT / "ruff.toml")
    lint_config = cast(dict[str, Any], ruff_config["lint"])

    assert lint_config["select"] == ["ALL"]
    assert lint_config["preview"] is True
    assert lint_config["explicit-preview-rules"] is True


def test_makefile_quality_targets_use_prek() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    format_recipe = _make_target_recipe(makefile=makefile, target="format")
    lint_recipe = _make_target_recipe(makefile=makefile, target="lint")

    assert any(command.startswith("uv run prek run") for command in format_recipe)
    assert "uv run prek run --all-files" in lint_recipe


def _prek_hooks_by_name() -> dict[str, dict[str, Any]]:
    prek_config = _read_toml(REPO_ROOT / "prek.toml")
    repos = cast(list[dict[str, Any]], prek_config["repos"])
    return {
        hook["name"]: hook
        for repo in repos
        for hook in cast(list[dict[str, Any]], repo.get("hooks", []))
        if "name" in hook
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
