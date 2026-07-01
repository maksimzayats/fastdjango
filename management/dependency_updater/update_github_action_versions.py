import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from management.dependency_updater.action_update import ActionUpdate
from management.dependency_updater.http import _json_response
from management.dependency_updater.parallel import _resolve_in_parallel

_VersionResolver = Callable[[str], str | None]

_ACTION_USES_RE = re.compile(
    r"(?P<prefix>\buses:\s*)(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@(?P<ref>[^\s#]+)",
)
_YAML_VERSION_RE = re.compile(
    r"^(?P<prefix>\s*version:\s*)(?P<ref>[^\s#]+)(?P<suffix>\s*(?:#.*)?)(?P<newline>\r?\n?)$",
)
_MAJOR_REF_RE = re.compile(r"v(?P<major>\d+)")
_SETUP_COMPOSE_ACTION_REPOSITORY = "docker/setup-compose-action"
_DOCKER_COMPOSE_REPOSITORY = "docker/compose"


def update_github_action_versions(
    *,
    repo_root: Path,
    dry_run: bool = False,
    latest_tag_resolver: _VersionResolver | None = None,
) -> tuple[ActionUpdate, ...]:
    """Update GitHub Action major-version pins.

    Args:
        repo_root: Repository root containing `.github/workflows`.
        dry_run: Whether to return updates without writing workflow files.
        latest_tag_resolver: Optional resolver used by tests or custom runs.

    Returns:
        GitHub Action updates that were applied or planned.
    """
    workflows_path = repo_root / ".github" / "workflows"
    if not workflows_path.exists():
        return ()

    resolver = latest_tag_resolver or _latest_github_tag
    workflow_texts = {
        workflow_path: workflow_path.read_text(encoding="utf-8")
        for workflow_path in _workflow_paths(workflows_path=workflows_path)
    }
    repositories = _github_action_repositories(workflow_texts=tuple(workflow_texts.values()))
    latest_tags = _resolve_in_parallel(entries=repositories, resolver=resolver)
    tool_repositories = _workflow_tool_repositories(workflow_texts=tuple(workflow_texts.values()))
    latest_tool_tags = _resolve_in_parallel(entries=tool_repositories, resolver=resolver)

    updates: list[ActionUpdate] = []
    for workflow_path, workflow_text in workflow_texts.items():
        updated_text, workflow_updates = _updated_workflow_action_text(
            workflow_path=workflow_path,
            workflow_text=workflow_text,
            latest_tags=latest_tags,
            latest_tool_tags=latest_tool_tags,
        )
        updates.extend(workflow_updates)
        if workflow_updates and not dry_run:
            workflow_path.write_text(updated_text, encoding="utf-8")

    return tuple(updates)


def _updated_action_ref(*, current_ref: str, latest_tag: str) -> str:
    current_major = _major_version(ref=current_ref)
    latest_major = _major_version(ref=latest_tag)

    if current_major is None or latest_major is None:
        return current_ref

    if current_major == latest_major:
        return current_ref

    return latest_tag


def _updated_workflow_action_text(
    *,
    workflow_path: Path,
    workflow_text: str,
    latest_tags: dict[str, str | None],
    latest_tool_tags: dict[str, str | None],
) -> tuple[str, tuple[ActionUpdate, ...]]:
    workflow_updates: list[ActionUpdate] = []

    def replace_action(match: re.Match[str]) -> str:
        repository = match.group("repository")
        old_ref = match.group("ref")
        latest_tag = latest_tags.get(repository)
        if latest_tag is None:
            return match.group(0)

        new_ref = _updated_action_ref(current_ref=old_ref, latest_tag=latest_tag)
        if new_ref == old_ref:
            return match.group(0)

        workflow_updates.append(
            ActionUpdate(
                file_path=workflow_path,
                repository=repository,
                old_ref=old_ref,
                new_ref=new_ref,
            ),
        )
        return f"{match.group('prefix')}{repository}@{new_ref}"

    updated_text = _ACTION_USES_RE.sub(replace_action, workflow_text)
    updated_text, setup_compose_updates = _updated_setup_compose_version_text(
        workflow_path=workflow_path,
        workflow_text=updated_text,
        latest_tool_tags=latest_tool_tags,
    )
    workflow_updates.extend(setup_compose_updates)

    return updated_text, tuple(workflow_updates)


def _workflow_paths(*, workflows_path: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(path for pattern in ("*.yml", "*.yaml") for path in workflows_path.glob(pattern)),
    )


def _github_action_repositories(*, workflow_texts: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                match.group("repository")
                for workflow_text in workflow_texts
                for match in _ACTION_USES_RE.finditer(workflow_text)
            },
        ),
    )


def _workflow_tool_repositories(*, workflow_texts: tuple[str, ...]) -> tuple[str, ...]:
    if any(
        _setup_compose_version_refs(workflow_text=workflow_text) for workflow_text in workflow_texts
    ):
        return (_DOCKER_COMPOSE_REPOSITORY,)

    return ()


def _updated_setup_compose_version_text(
    *,
    workflow_path: Path,
    workflow_text: str,
    latest_tool_tags: dict[str, str | None],
) -> tuple[str, tuple[ActionUpdate, ...]]:
    latest_version = latest_tool_tags.get(_DOCKER_COMPOSE_REPOSITORY)
    if latest_version is None:
        return workflow_text, ()

    updated_lines: list[str] = []
    updates: list[ActionUpdate] = []
    in_setup_compose_step = False
    action_indent: int | None = None
    for line in workflow_text.splitlines(keepends=True):
        stripped_line = line.lstrip()
        line_indent = len(line) - len(stripped_line)
        if (
            in_setup_compose_step
            and action_indent is not None
            and line_indent <= action_indent
            and stripped_line.startswith("- ")
        ):
            in_setup_compose_step = False
            action_indent = None

        if f"uses: {_SETUP_COMPOSE_ACTION_REPOSITORY}@" in stripped_line:
            in_setup_compose_step = True
            action_indent = line_indent

        updated_line, update = _updated_setup_compose_version_line(
            workflow_path=workflow_path,
            line=line,
            latest_version=latest_version,
            in_setup_compose_step=in_setup_compose_step,
        )
        updated_lines.append(updated_line)
        if update is not None:
            updates.append(update)

    return "".join(updated_lines), tuple(updates)


def _updated_setup_compose_version_line(
    *,
    workflow_path: Path,
    line: str,
    latest_version: str,
    in_setup_compose_step: bool,
) -> tuple[str, ActionUpdate | None]:
    if not in_setup_compose_step:
        return line, None

    match = _YAML_VERSION_RE.match(line)
    if match is None:
        return line, None

    old_version = match.group("ref")
    if old_version == latest_version:
        return line, None

    return (
        f"{match.group('prefix')}{latest_version}{match.group('suffix')}{match.group('newline')}",
        ActionUpdate(
            file_path=workflow_path,
            repository=_DOCKER_COMPOSE_REPOSITORY,
            old_ref=old_version,
            new_ref=latest_version,
        ),
    )


def _setup_compose_version_refs(*, workflow_text: str) -> tuple[str, ...]:
    refs: list[str] = []
    in_setup_compose_step = False
    action_indent: int | None = None
    for line in workflow_text.splitlines():
        stripped_line = line.lstrip()
        line_indent = len(line) - len(stripped_line)
        if (
            in_setup_compose_step
            and action_indent is not None
            and line_indent <= action_indent
            and stripped_line.startswith("- ")
        ):
            in_setup_compose_step = False
            action_indent = None

        if f"uses: {_SETUP_COMPOSE_ACTION_REPOSITORY}@" in stripped_line:
            in_setup_compose_step = True
            action_indent = line_indent

        if in_setup_compose_step:
            match = _YAML_VERSION_RE.match(line)
            if match is not None:
                refs.append(match.group("ref"))

    return tuple(refs)


def _major_version(*, ref: str) -> int | None:
    match = _MAJOR_REF_RE.match(ref)
    if match is None:
        return None

    return int(match.group("major"))


def _latest_github_tag(repository: str) -> str | None:
    latest_release = _github_json(url=f"https://api.github.com/repos/{repository}/releases/latest")
    if latest_release is not None and isinstance(latest_release.get("tag_name"), str):
        return cast(str, latest_release["tag_name"])

    tags = _github_json(url=f"https://api.github.com/repos/{repository}/tags?per_page=1")
    if isinstance(tags, list) and tags:
        tag = tags[0]
        if isinstance(tag, dict) and isinstance(tag.get("name"), str):
            return cast(str, tag["name"])

    return None


def _github_json(*, url: str) -> Any | None:
    response = _json_response(
        url=url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "modern-python-template-dependency-updater",
        },
    )
    if response is None:
        return None

    return response.payload
