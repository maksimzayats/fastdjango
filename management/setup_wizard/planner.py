from __future__ import annotations

import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from management.setup_wizard.config import (
    update_docker_compose_yaml,
    update_mkdocs_yaml,
    update_prek_toml,
    update_pyproject_toml,
    update_ruff_toml,
)
from management.setup_wizard.env import (
    build_env_content,
    build_env_example_content,
    build_test_env_example_content,
)
from management.setup_wizard.file_operations import FilePlan
from management.setup_wizard.models import SetupAnswers
from management.setup_wizard.python_rewrite import rewrite_python_imports
from management.setup_wizard.readme import build_project_readme
from management.setup_wizard.text_rewrite import (
    ProjectReferences,
    replace_project_references,
)

DEFAULT_PACKAGE_NAME = "fastdjango"
EXCLUDED_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "htmlcov",
    "site",
}


def build_setup_plan(
    *,
    repo_root: Path,
    answers: SetupAnswers,
    current_package_name: str | None = None,
) -> FilePlan:
    resolved_package_name = current_package_name or detect_current_package_name(repo_root=repo_root)
    plan = FilePlan(repo_root=repo_root)

    _plan_package_rename(
        plan=plan,
        answers=answers,
        current_package_name=resolved_package_name,
    )
    _plan_python_rewrites(
        plan=plan,
        answers=answers,
        current_package_name=resolved_package_name,
    )
    _plan_config_rewrites(
        plan=plan,
        answers=answers,
        current_package_name=resolved_package_name,
    )
    _plan_environment_files(plan=plan, answers=answers)
    _plan_docs(plan=plan, answers=answers, current_package_name=resolved_package_name)
    _plan_self_delete(plan=plan, answers=answers)
    plan.add_command(("uv", "lock"), detail="Refresh uv.lock")
    return plan


def detect_current_package_name(*, repo_root: Path) -> str:
    pyproject_path = repo_root / "pyproject.toml"
    if pyproject_path.exists():
        package_name = _detect_package_name_from_pyproject(pyproject_path=pyproject_path)
        if package_name is not None:
            return package_name

    src_path = repo_root / "src"
    if not src_path.exists():
        return DEFAULT_PACKAGE_NAME

    package_dirs = sorted(path.name for path in src_path.iterdir() if _is_python_package(path))
    if len(package_dirs) == 1:
        return package_dirs[0]

    return DEFAULT_PACKAGE_NAME


def _detect_package_name_from_pyproject(*, pyproject_path: Path) -> str | None:
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    django_settings_module = (
        pyproject.get("tool", {}).get("django-stubs", {}).get("django_settings_module")
    )
    if isinstance(django_settings_module, str) and "." in django_settings_module:
        return django_settings_module.split(".", maxsplit=1)[0]

    return None


def _plan_package_rename(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    source_path = plan.repo_root / "src" / current_package_name
    target_path = plan.repo_root / "src" / answers.package_name
    plan.add_rename(source_path, target_path, detail="Rename Python package")


def _plan_python_rewrites(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    for source_path in _iter_python_files(repo_root=plan.repo_root, answers=answers):
        content = source_path.read_text(encoding="utf-8")
        content = rewrite_python_imports(
            source=content,
            old_package_name=current_package_name,
            new_package_name=answers.package_name,
        )
        content = _replace_text_references(
            text=content,
            answers=answers,
            current_package_name=current_package_name,
        )
        plan.add_write(
            _target_path_for_package_rename(
                source_path=source_path,
                repo_root=plan.repo_root,
                current_package_name=current_package_name,
                new_package_name=answers.package_name,
            ),
            content=content,
            detail="Rewrite Python package references",
        )


def _plan_config_rewrites(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    _rewrite_config_file(
        plan=plan,
        relative_path="pyproject.toml",
        rewrite=lambda content: update_pyproject_toml(
            content,
            answers=answers,
            old_package_name=current_package_name,
        ),
    )
    _rewrite_config_file(
        plan=plan,
        relative_path="ruff.toml",
        rewrite=lambda content: update_ruff_toml(content, package_name=answers.package_name),
    )
    _rewrite_config_file(plan=plan, relative_path="prek.toml", rewrite=update_prek_toml)
    _rewrite_config_file(
        plan=plan,
        relative_path="docker/docker-compose.yaml",
        rewrite=lambda content: update_docker_compose_yaml(
            content,
            answers=answers,
            old_package_name=current_package_name,
            is_local_overlay=False,
        ),
    )
    _rewrite_config_file(
        plan=plan,
        relative_path="docker/docker-compose.local.yaml",
        rewrite=lambda content: update_docker_compose_yaml(
            content,
            answers=answers,
            old_package_name=current_package_name,
            is_local_overlay=True,
        ),
    )
    _rewrite_config_file(
        plan=plan,
        relative_path="docker/docker-compose.test.yaml",
        rewrite=lambda content: update_docker_compose_yaml(
            content,
            answers=answers,
            old_package_name=current_package_name,
            is_local_overlay=True,
        ),
    )
    _rewrite_makefile(plan=plan, answers=answers, current_package_name=current_package_name)


def _plan_environment_files(*, plan: FilePlan, answers: SetupAnswers) -> None:
    env_path = plan.repo_root / ".env"
    if answers.overwrite_env or not env_path.exists():
        plan.add_write(
            env_path,
            content=build_env_content(answers=answers),
            detail="Write generated .env",
        )

    plan.add_write(
        plan.repo_root / ".env.example",
        content=build_env_example_content(answers=answers),
        detail="Update .env.example",
    )
    plan.add_write(
        plan.repo_root / ".env.test.example",
        content=build_test_env_example_content(),
        detail="Update .env.test.example",
    )


def _plan_docs(*, plan: FilePlan, answers: SetupAnswers, current_package_name: str) -> None:
    readme_path = plan.repo_root / "README.md"
    if readme_path.exists():
        plan.add_write(
            readme_path,
            content=build_project_readme(answers=answers),
            detail="Rewrite README for generated project",
        )

    docs_path = plan.repo_root / "docs"
    if not answers.keep_docs:
        plan.add_delete(docs_path, detail="Remove documentation")
        return

    _rewrite_docs_files(plan=plan, answers=answers, current_package_name=current_package_name)


def _plan_self_delete(*, plan: FilePlan, answers: SetupAnswers) -> None:
    if not answers.delete_wizard:
        return

    plan.add_delete(plan.repo_root / "management" / "setup_wizard", detail="Remove setup wizard")
    plan.add_delete(plan.repo_root / "tests" / "setup_wizard", detail="Remove setup wizard tests")


def _rewrite_config_file(
    *,
    plan: FilePlan,
    relative_path: str,
    rewrite: ConfigRewrite,
) -> None:
    path = plan.repo_root / relative_path
    if not path.exists():
        return

    plan.add_write(
        path,
        content=rewrite(path.read_text(encoding="utf-8")),
        detail=f"Update {relative_path}",
    )


def _rewrite_makefile(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    path = plan.repo_root / "Makefile"
    if not path.exists():
        return

    content = _replace_text_references(
        text=path.read_text(encoding="utf-8"),
        answers=answers,
        current_package_name=current_package_name,
    )
    content = (
        _ensure_setup_target(content)
        if not answers.delete_wizard
        else _remove_setup_target(content)
    )
    content = _remove_docs_targets(content) if not answers.keep_docs else content
    plan.add_write(path, content=content, detail="Update Makefile")


def _rewrite_docs_files(
    *,
    plan: FilePlan,
    answers: SetupAnswers,
    current_package_name: str,
) -> None:
    mkdocs_path = plan.repo_root / "docs" / "mkdocs.yml"
    if mkdocs_path.exists():
        plan.add_write(
            mkdocs_path,
            content=update_mkdocs_yaml(
                mkdocs_path.read_text(encoding="utf-8"),
                answers=answers,
                old_package_name=current_package_name,
            ),
            detail="Update MkDocs config",
        )

    for path in (plan.repo_root / "docs").rglob("*"):
        if not path.is_file() or path == mkdocs_path:
            continue
        if path.suffix not in {".md", ".yml", ".yaml", ".txt"} and path.name != "CNAME":
            continue

        if path.name == "CNAME" and answers.docs_site_url is None:
            plan.add_delete(path, detail="Remove docs custom domain")
            continue

        content = _replace_text_references(
            text=path.read_text(encoding="utf-8"),
            answers=answers,
            current_package_name=current_package_name,
        )
        if path.name == "CNAME" and answers.docs_site_url is not None:
            content = f"{urlsplit(answers.docs_site_url).netloc}\n"
        plan.add_write(path, content=content, detail=f"Update {plan.relative_path(path)}")


def _iter_python_files(*, repo_root: Path, answers: SetupAnswers) -> list[Path]:
    paths: list[Path] = []
    for base_path in (repo_root / "src", repo_root / "tests", repo_root / "management"):
        if not base_path.exists():
            continue
        for path in base_path.rglob("*.py"):
            if _is_excluded_path(path=path):
                continue
            if answers.delete_wizard and _is_wizard_path(path=path, repo_root=repo_root):
                continue
            paths.append(path)

    return paths


def _target_path_for_package_rename(
    *,
    source_path: Path,
    repo_root: Path,
    current_package_name: str,
    new_package_name: str,
) -> Path:
    old_package_root = repo_root / "src" / current_package_name
    try:
        return repo_root / "src" / new_package_name / source_path.relative_to(old_package_root)
    except ValueError:
        return source_path


def _replace_text_references(
    *,
    text: str,
    answers: SetupAnswers,
    current_package_name: str,
) -> str:
    return replace_project_references(
        text=text,
        references=ProjectReferences(
            old_package_name=current_package_name,
            new_package_name=answers.package_name,
            project_name=answers.project_name,
            docs_site_url=answers.docs_site_url,
        ),
    )


def _ensure_setup_target(content: str) -> str:
    if "\nsetup:\n" in content:
        return content

    return (
        content.rstrip()
        + "\n\nsetup:\n\tuv run --group setup python -m management.setup_wizard $(ARGS)\n"
    )


def _remove_setup_target(content: str) -> str:
    content = re.sub(
        pattern=r"\nsetup:\n\tuv run --group setup python -m management\.setup_wizard \$\(ARGS\)\n",
        repl="\n",
        string=content,
    )
    return content.replace(" setup ", " ").replace(" setup\n", "\n")


def _remove_docs_targets(content: str) -> str:
    content = re.sub(
        pattern=r"\n(?:\.PHONY: docs docs-build\n)?docs:\n\t.*\n",
        repl="\n",
        string=content,
    )
    content = re.sub(pattern=r"\ndocs-build:\n\t.*\n", repl="\n", string=content)
    return content.replace(" docs docs-build", "")


def _is_python_package(path: Path) -> bool:
    return path.is_dir() and (path / "__init__.py").exists()


def _is_excluded_path(*, path: Path) -> bool:
    return any(part in EXCLUDED_DIR_NAMES for part in path.parts)


def _is_wizard_path(*, path: Path, repo_root: Path) -> bool:
    for wizard_path in (
        repo_root / "management" / "setup_wizard",
        repo_root / "tests" / "setup_wizard",
    ):
        try:
            path.relative_to(wizard_path)
        except ValueError:
            continue

        return True

    return False


type ConfigRewrite = Callable[[str], str]
