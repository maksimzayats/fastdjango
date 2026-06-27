from __future__ import annotations

import argparse
import itertools
import json
import re
import subprocess
import sys
import threading
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Hashable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any, Self, cast

VersionResolver = Callable[[str], str | None]
ContainerTagResolver = Callable[[str, str | None], str | None]

_ACTION_USES_RE = re.compile(
    r"(?P<prefix>\buses:\s*)(?P<repository>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@(?P<ref>[^\s#]+)",
)
_YAML_VERSION_RE = re.compile(
    r"^(?P<prefix>\s*version:\s*)(?P<ref>[^\s#]+)(?P<suffix>\s*(?:#.*)?)(?P<newline>\r?\n?)$",
)
_COMPOSE_IMAGE_RE = re.compile(
    r"^(?P<prefix>\s*image:\s*[\"']?)(?P<image>[^\s\"']+)(?P<suffix>[\"']?\s*(?:#.*)?)$",
    re.MULTILINE,
)
_DOCKER_FROM_RE = re.compile(
    r"^(?P<prefix>\s*FROM\s+(?:--platform=\S+\s+)?)(?P<image>[^\s]+)(?P<suffix>.*)$",
    re.IGNORECASE | re.MULTILINE,
)
_MAJOR_REF_RE = re.compile(r"v(?P<major>\d+)")
_NAME_RE = re.compile(r"(?P<name>[A-Za-z0-9_.-]+)(?P<extras>\[[^\]]+\])?")
_LOWER_BOUND_RE = re.compile(r"(?P<operator>>=|>)\s*[^,; ]+")
_UPPER_BOUND_RE = re.compile(r"(?:^|,)\s*(?P<operator><=|<)\s*(?P<version>[^,; ]+)")
_VERSION_PREFIX_RE = re.compile(r"(?P<release>\d+(?:\.\d+)*)")
_CONTAINER_VERSION_RE = re.compile(
    r"(?P<prefix>.*?)(?P<version>v?\d+(?:\.\d+)*)(?P<suffix>$|[-_].*)",
)
_RELEASE_TAG_RE = re.compile(
    r"^RELEASE\.(?P<date>\d{4}-\d{2}-\d{2})T(?P<time>\d{2}-\d{2}-\d{2})Z(?P<suffix>.*)$",
)
_CONTAINER_BUILD_SUFFIX_RE = re.compile(r"-p(?P<build>\d+)$")
_GHCR_NEXT_LINK_RE = re.compile(r'<(?P<url>[^>]+)>;\s*rel="next"')
_CONTAINER_REF_LEADING_BOUNDARY = r"(?<![A-Za-z0-9_.:/@-])"
_CONTAINER_REF_TRAILING_BOUNDARY = r"(?!(?:[A-Za-z0-9_:/@-]|\.[A-Za-z0-9_]))"
_CONTAINER_REFERENCE_SUFFIXES = {".md", ".yaml", ".yml"}
_MAX_REGISTRY_PAGES = 20
_MAX_PARALLEL_WORKERS = 8
_PYTHON_VERSION_PREFIX_LENGTH = 2
_SPINNER_CLEAR_EXTRA_WIDTH = 8
_SPINNER_INTERVAL_SECONDS = 0.1
_SETUP_COMPOSE_ACTION_REPOSITORY = "docker/setup-compose-action"
_DOCKER_COMPOSE_REPOSITORY = "docker/compose"


@dataclass(frozen=True, kw_only=True)
class DependencyUpdate:
    old_requirement: str
    new_requirement: str


@dataclass(frozen=True, kw_only=True)
class ActionUpdate:
    file_path: Path
    repository: str
    old_ref: str
    new_ref: str


@dataclass(frozen=True, kw_only=True)
class ContainerImageUpdate:
    file_path: Path
    old_ref: str
    new_ref: str


@dataclass(frozen=True, kw_only=True)
class UpdateSummary:
    dependency_updates: tuple[DependencyUpdate, ...]
    action_updates: tuple[ActionUpdate, ...]
    container_updates: tuple[ContainerImageUpdate, ...]


@dataclass(frozen=True, kw_only=True)
class UpdateOptions:
    dry_run: bool = False
    upgrade_lock: bool = True
    update_pyproject: bool = True
    update_actions: bool = True
    update_containers: bool = True


@dataclass(frozen=True, kw_only=True)
class ContainerImageReference:
    file_path: Path
    image_ref: str


@dataclass(frozen=True, kw_only=True)
class ContainerImage:
    repository: str
    tag: str | None
    digest: str | None


@dataclass(frozen=True, kw_only=True)
class ContainerTagVersion:
    prefix: str
    version: tuple[int, ...]
    suffix: str


@dataclass(frozen=True, kw_only=True)
class JsonResponse:
    payload: Any
    link: str | None


class ProgressReporter:
    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled

    def step(self, message: str, *, spinner: bool = True) -> _ProgressStep:
        return _ProgressStep(
            message=message,
            enabled=self._enabled,
            spinner=spinner,
        )


class _ProgressStep:
    def __init__(self, *, message: str, enabled: bool, spinner: bool) -> None:
        self._message = message
        self._enabled = enabled
        self._spinner = spinner
        self._stop_event: threading.Event | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> Self:
        if not self._enabled:
            return self

        if self._use_spinner:
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
            return self

        _write_line(f"{self._message}...")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        if not self._enabled:
            return

        if self._thread is not None and self._stop_event is not None:
            self._stop_event.set()
            self._thread.join()
            clear_width = len(self._message) + _SPINNER_CLEAR_EXTRA_WIDTH
            sys.stdout.write(f"\r{' ' * clear_width}\r")

        status = "failed" if exc_type is not None else "done"
        _write_line(f"{self._message}: {status}")

    @property
    def _use_spinner(self) -> bool:
        return self._spinner and sys.stdout.isatty()

    def _spin(self) -> None:
        stop_event = self._stop_event
        if stop_event is None:
            return

        for frame in itertools.cycle("|/-\\"):
            sys.stdout.write(f"\r{frame} {self._message}...")
            sys.stdout.flush()
            if stop_event.wait(_SPINNER_INTERVAL_SECONDS):
                return


def update_dependencies(
    *,
    repo_root: Path,
    options: UpdateOptions | None = None,
    progress: ProgressReporter | None = None,
) -> UpdateSummary:
    update_options = options or UpdateOptions()
    progress_reporter = progress or ProgressReporter(enabled=False)

    if update_options.upgrade_lock and not update_options.dry_run:
        with progress_reporter.step("Updating uv.lock", spinner=False):
            _run_command(["uv", "lock", "--upgrade"], repo_root=repo_root)

    dependency_updates: tuple[DependencyUpdate, ...] = ()
    if update_options.update_pyproject:
        with progress_reporter.step("Syncing pyproject.toml dependency bounds"):
            dependency_updates = sync_pyproject_dependency_versions(
                repo_root=repo_root,
                dry_run=update_options.dry_run,
            )

    action_updates: tuple[ActionUpdate, ...] = ()
    if update_options.update_actions:
        with progress_reporter.step("Checking GitHub Action pins"):
            action_updates = update_github_action_versions(
                repo_root=repo_root,
                dry_run=update_options.dry_run,
            )

    container_updates: tuple[ContainerImageUpdate, ...] = ()
    if update_options.update_containers:
        with progress_reporter.step("Checking Docker and Compose image pins"):
            container_updates = update_container_image_versions(
                repo_root=repo_root,
                dry_run=update_options.dry_run,
            )

    if dependency_updates and not update_options.dry_run:
        with progress_reporter.step("Refreshing uv.lock", spinner=False):
            _run_command(["uv", "lock"], repo_root=repo_root)

    return UpdateSummary(
        dependency_updates=dependency_updates,
        action_updates=action_updates,
        container_updates=container_updates,
    )


def sync_pyproject_dependency_versions(
    *,
    repo_root: Path,
    dry_run: bool = False,
    latest_version_resolver: VersionResolver | None = None,
) -> tuple[DependencyUpdate, ...]:
    pyproject_path = repo_root / "pyproject.toml"
    uv_lock_path = repo_root / "uv.lock"

    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    pyproject_data = _read_toml(pyproject_path)
    locked_versions = _locked_versions(uv_lock_path=uv_lock_path)
    resolver = latest_version_resolver or _latest_pypi_version

    updates: list[DependencyUpdate] = []
    updated_text = pyproject_text
    for requirement in _direct_requirements(pyproject_data=pyproject_data):
        target_version = _target_dependency_version(
            requirement=requirement,
            locked_versions=locked_versions,
            latest_version_resolver=resolver,
        )
        if target_version is None:
            continue

        updated_requirement = _with_lower_bound(
            requirement=requirement,
            version=target_version,
        )
        if updated_requirement == requirement:
            continue

        old_fragment = f'"{requirement}"'
        new_fragment = f'"{updated_requirement}"'
        if old_fragment not in updated_text:
            msg = f"Could not find dependency requirement in pyproject.toml: {requirement}"
            raise RuntimeError(msg)

        updated_text = updated_text.replace(old_fragment, new_fragment, 1)
        updates.append(
            DependencyUpdate(
                old_requirement=requirement,
                new_requirement=updated_requirement,
            ),
        )

    if updates and not dry_run:
        pyproject_path.write_text(updated_text, encoding="utf-8")

    return tuple(updates)


def update_github_action_versions(
    *,
    repo_root: Path,
    dry_run: bool = False,
    latest_tag_resolver: VersionResolver | None = None,
) -> tuple[ActionUpdate, ...]:
    workflows_path = repo_root / ".github" / "workflows"
    if not workflows_path.exists():
        return ()

    resolver = latest_tag_resolver or _latest_github_tag
    workflow_texts = {
        workflow_path: workflow_path.read_text(encoding="utf-8")
        for workflow_path in _workflow_paths(workflows_path=workflows_path)
    }
    repositories = _github_action_repositories(workflow_texts=tuple(workflow_texts.values()))
    latest_tags = _resolve_in_parallel(items=repositories, resolver=resolver)
    tool_repositories = _workflow_tool_repositories(workflow_texts=tuple(workflow_texts.values()))
    latest_tool_tags = _resolve_in_parallel(items=tool_repositories, resolver=resolver)

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


def update_container_image_versions(
    *,
    repo_root: Path,
    dry_run: bool = False,
    latest_tag_resolver: ContainerTagResolver | None = None,
) -> tuple[ContainerImageUpdate, ...]:
    references = _container_image_references(repo_root=repo_root)
    resolver = latest_tag_resolver or _latest_container_image_tag
    replacements = _container_image_replacements(
        references=references,
        latest_tag_resolver=resolver,
    )
    if not replacements:
        return ()

    return _replace_container_refs(
        repo_root=repo_root,
        replacements=replacements,
        dry_run=dry_run,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Update uv lock, pyproject dependency lower bounds, "
            "GitHub Action pins, and container image pins."
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to update. Defaults to the current directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing files or running uv lock --upgrade.",
    )
    parser.add_argument(
        "--skip-lock-upgrade",
        action="store_true",
        help="Do not run uv lock --upgrade before syncing pyproject.toml.",
    )
    parser.add_argument(
        "--skip-pyproject",
        action="store_true",
        help="Do not sync pyproject.toml dependency lower bounds.",
    )
    parser.add_argument(
        "--skip-actions",
        action="store_true",
        help="Do not update GitHub Action versions in .github/workflows.",
    )
    parser.add_argument(
        "--skip-containers",
        action="store_true",
        help="Do not update Dockerfile or Docker Compose image pins.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Hide updater progress messages.",
    )
    args = parser.parse_args(argv)

    summary = update_dependencies(
        repo_root=args.repo_root,
        options=UpdateOptions(
            dry_run=args.dry_run,
            upgrade_lock=not args.skip_lock_upgrade,
            update_pyproject=not args.skip_pyproject,
            update_actions=not args.skip_actions,
            update_containers=not args.skip_containers,
        ),
        progress=ProgressReporter(enabled=not args.quiet),
    )

    _print_summary(summary=summary, dry_run=args.dry_run)
    return 0


def _direct_requirements(*, pyproject_data: dict[str, Any]) -> tuple[str, ...]:
    requirements: list[str] = []

    project = cast(dict[str, Any], pyproject_data["project"])
    requirements.extend(cast(list[str], project.get("dependencies", [])))

    dependency_groups = cast(dict[str, list[str]], pyproject_data.get("dependency-groups", {}))
    for group_requirements in dependency_groups.values():
        requirements.extend(group_requirements)

    build_system = cast(dict[str, Any], pyproject_data.get("build-system", {}))
    requirements.extend(cast(list[str], build_system.get("requires", [])))

    return tuple(requirements)


def _target_dependency_version(
    *,
    requirement: str,
    locked_versions: dict[str, str],
    latest_version_resolver: VersionResolver,
) -> str | None:
    dependency_name = _requirement_name(requirement=requirement)
    if dependency_name is None:
        return None

    canonical_name = _canonical_name(dependency_name)
    target_version = locked_versions.get(canonical_name)
    if target_version is None:
        target_version = latest_version_resolver(dependency_name)

    if target_version is None:
        return None

    if not _satisfies_upper_bounds(requirement=requirement, version=target_version):
        return None

    return target_version


def _locked_versions(*, uv_lock_path: Path) -> dict[str, str]:
    uv_lock = _read_toml(uv_lock_path)
    packages = cast(list[dict[str, Any]], uv_lock.get("package", []))
    return {
        _canonical_name(cast(str, package["name"])): cast(str, package["version"])
        for package in packages
    }


def _read_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _requirement_name(*, requirement: str) -> str | None:
    match = _NAME_RE.match(requirement)
    if match is None:
        return None

    return match.group("name")


def _with_lower_bound(*, requirement: str, version: str) -> str:
    marker_prefix, separator, marker_suffix = requirement.partition(";")
    match = _NAME_RE.match(marker_prefix)
    if match is None:
        return requirement

    name = match.group("name")
    extras = match.group("extras") or ""
    requirement_prefix = f"{name}{extras}"
    specifier = marker_prefix[match.end() :].strip()

    if not specifier:
        updated = f"{requirement_prefix}>={version}"
    elif _LOWER_BOUND_RE.search(specifier):
        updated_specifier = _LOWER_BOUND_RE.sub(f">={version}", specifier, count=1)
        updated = f"{requirement_prefix}{updated_specifier}"
    else:
        updated = f"{requirement_prefix}>={version},{specifier}"

    if not separator:
        return updated

    return f"{updated};{marker_suffix}"


def _updated_action_ref(*, current_ref: str, latest_tag: str) -> str:
    current_major = _major_version(ref=current_ref)
    latest_major = _major_version(ref=latest_tag)

    if current_major is None or latest_major is None:
        return current_ref

    if current_major == latest_major:
        return current_ref

    return latest_tag


def _resolve_in_parallel[ResolveKey: Hashable, ResolveValue](
    *,
    items: tuple[ResolveKey, ...],
    resolver: Callable[[ResolveKey], ResolveValue],
) -> dict[ResolveKey, ResolveValue]:
    if not items:
        return {}

    max_workers = min(_MAX_PARALLEL_WORKERS, len(items))
    results: dict[ResolveKey, ResolveValue] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(resolver, item): item for item in items}
        for future in as_completed(futures):
            item = futures[future]
            results[item] = future.result()

    return results


def _satisfies_upper_bounds(*, requirement: str, version: str) -> bool:
    marker_prefix, _, _ = requirement.partition(";")
    match = _NAME_RE.match(marker_prefix)
    if match is None:
        return True

    specifier = marker_prefix[match.end() :].strip()
    for upper_bound in _UPPER_BOUND_RE.finditer(specifier):
        comparison = _compare_versions(version, upper_bound.group("version"))
        if comparison is None:
            return False

        if upper_bound.group("operator") == "<" and comparison >= 0:
            return False

        if upper_bound.group("operator") == "<=" and comparison > 0:
            return False

    return True


def _compare_versions(left: str, right: str) -> int | None:
    left_key = _version_key(version=left)
    right_key = _version_key(version=right)
    if left_key is None or right_key is None:
        return None

    max_length = max(len(left_key), len(right_key))
    normalized_left = left_key + (0,) * (max_length - len(left_key))
    normalized_right = right_key + (0,) * (max_length - len(right_key))

    if normalized_left < normalized_right:
        return -1

    if normalized_left > normalized_right:
        return 1

    return 0


def _version_key(*, version: str) -> tuple[int, ...] | None:
    match = _VERSION_PREFIX_RE.match(version)
    if match is None:
        return None

    return tuple(int(part) for part in match.group("release").split("."))


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


def _container_image_references(*, repo_root: Path) -> tuple[ContainerImageReference, ...]:
    references: list[ContainerImageReference] = []
    for path in _container_definition_paths(repo_root=repo_root):
        text = path.read_text(encoding="utf-8")
        references.extend(
            ContainerImageReference(file_path=path, image_ref=image_ref)
            for image_ref in _container_image_refs_from_text(text=text)
        )

    return tuple(references)


def _container_definition_paths(*, repo_root: Path) -> tuple[Path, ...]:
    paths: set[Path] = set()

    for path in repo_root.iterdir():
        if path.is_file() and _is_container_definition_path(path=path):
            paths.add(path)

    docker_path = repo_root / "docker"
    if docker_path.exists():
        for path in docker_path.rglob("*"):
            if path.is_file() and _is_container_definition_path(path=path):
                paths.add(path)

    return tuple(sorted(paths))


def _is_container_definition_path(*, path: Path) -> bool:
    name = path.name.lower()
    if name.startswith("dockerfile"):
        return True

    return name in {"compose.yaml", "compose.yml"} or name.startswith("docker-compose")


def _container_image_refs_from_text(*, text: str) -> tuple[str, ...]:
    references: list[str] = []
    for pattern in (_COMPOSE_IMAGE_RE, _DOCKER_FROM_RE):
        references.extend(match.group("image") for match in pattern.finditer(text))

    return tuple(references)


def _container_image_replacements(
    *,
    references: tuple[ContainerImageReference, ...],
    latest_tag_resolver: ContainerTagResolver,
) -> dict[str, str]:
    images = _remote_container_images(references=references)
    latest_tags = _resolve_container_tags(
        images=tuple(images.values()),
        latest_tag_resolver=latest_tag_resolver,
    )
    replacements: dict[str, str] = {}
    for image_ref, image in images.items():
        latest_tag = latest_tags.get((image.repository, image.tag))
        if latest_tag is None or latest_tag == image.tag:
            continue

        new_ref = _container_image_ref_with_tag(image=image, tag=latest_tag)
        if new_ref != image_ref:
            replacements[image_ref] = new_ref
            if _should_replace_bare_container_doc_ref(image=image, image_ref=image_ref):
                replacements.setdefault(image.repository, new_ref)

    return replacements


def _remote_container_images(
    *,
    references: tuple[ContainerImageReference, ...],
) -> dict[str, ContainerImage]:
    images: dict[str, ContainerImage] = {}
    for image_ref in sorted({reference.image_ref for reference in references}):
        image = _parse_container_image_ref(image_ref=image_ref)
        if image is None or _should_skip_container_image(image=image):
            continue

        images[image_ref] = image

    return images


def _resolve_container_tags(
    *,
    images: tuple[ContainerImage, ...],
    latest_tag_resolver: ContainerTagResolver,
) -> dict[tuple[str, str | None], str | None]:
    keys = tuple(sorted({(image.repository, image.tag) for image in images}))
    return _resolve_in_parallel(
        items=keys,
        resolver=lambda key: latest_tag_resolver(key[0], key[1]),
    )


def _parse_container_image_ref(*, image_ref: str) -> ContainerImage | None:
    if image_ref.startswith("${"):
        return None

    ref_without_digest, separator, digest = image_ref.partition("@")
    last_slash_index = ref_without_digest.rfind("/")
    tag_separator_index = ref_without_digest.rfind(":")
    if tag_separator_index > last_slash_index:
        repository = ref_without_digest[:tag_separator_index]
        tag = ref_without_digest[tag_separator_index + 1 :]
    else:
        repository = ref_without_digest
        tag = None

    if not repository:
        return None

    return ContainerImage(
        repository=repository,
        tag=tag or None,
        digest=digest if separator else None,
    )


def _should_skip_container_image(*, image: ContainerImage) -> bool:
    if image.digest is not None:
        return True

    if image.repository == "scratch" or image.repository.startswith("localhost/"):
        return True

    return image.tag == "local"


def _container_image_ref_with_tag(*, image: ContainerImage, tag: str) -> str:
    return f"{image.repository}:{tag}"


def _should_replace_bare_container_doc_ref(*, image: ContainerImage, image_ref: str) -> bool:
    return image.tag == "latest" and image_ref != image.repository and "/" in image.repository


def _replace_container_refs(
    *,
    repo_root: Path,
    replacements: dict[str, str],
    dry_run: bool,
) -> tuple[ContainerImageUpdate, ...]:
    updates: list[ContainerImageUpdate] = []
    ordered_replacements = sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)
    for path in _container_reference_paths(repo_root=repo_root):
        original_text = path.read_text(encoding="utf-8")
        updated_text = original_text
        for old_ref, new_ref in ordered_replacements:
            updated_text, changed = _replace_container_ref_in_text(
                text=updated_text,
                old_ref=old_ref,
                new_ref=new_ref,
            )
            if not changed:
                continue

            updates.append(
                ContainerImageUpdate(
                    file_path=path,
                    old_ref=old_ref,
                    new_ref=new_ref,
                ),
            )

        if updated_text != original_text and not dry_run:
            path.write_text(updated_text, encoding="utf-8")

    return tuple(updates)


def _replace_container_ref_in_text(*, text: str, old_ref: str, new_ref: str) -> tuple[str, bool]:
    updated_text = re.sub(_container_ref_pattern(image_ref=old_ref), new_ref, text)
    return updated_text, updated_text != text


def _container_ref_pattern(*, image_ref: str) -> str:
    return (
        f"{_CONTAINER_REF_LEADING_BOUNDARY}{re.escape(image_ref)}{_CONTAINER_REF_TRAILING_BOUNDARY}"
    )


def _container_reference_paths(*, repo_root: Path) -> tuple[Path, ...]:
    paths = set(_container_definition_paths(repo_root=repo_root))
    readme_path = repo_root / "README.md"
    if readme_path.exists():
        paths.add(readme_path)

    docs_path = repo_root / "docs"
    if docs_path.exists():
        for path in docs_path.rglob("*"):
            if path.is_file() and path.suffix in _CONTAINER_REFERENCE_SUFFIXES:
                paths.add(path)

    return tuple(sorted(paths))


def _latest_container_image_tag(repository: str, current_tag: str | None) -> str | None:
    tags = _container_registry_tags(repository=repository)
    if not tags:
        return None

    if current_tag is None or current_tag == "latest":
        return _best_ranked_container_tag(tags=tags)

    return _best_compatible_container_tag(
        repository=repository,
        current_tag=current_tag,
        tags=tags,
    )


def _container_registry_tags(*, repository: str) -> tuple[str, ...]:
    registry, repository_path = _container_registry_and_path(repository=repository)
    if registry == "docker.io":
        return _docker_hub_tags(repository_path=repository_path)

    if registry == "ghcr.io":
        return _ghcr_tags(repository_path=repository_path)

    return ()


def _container_registry_and_path(*, repository: str) -> tuple[str, str]:
    first_component, separator, remaining_path = repository.partition("/")
    if first_component == "docker.io" and separator:
        return "docker.io", _docker_hub_path(repository=remaining_path)

    has_registry = (
        "." in first_component or ":" in first_component or first_component == "localhost"
    )
    if has_registry and separator:
        return first_component, remaining_path

    return "docker.io", _docker_hub_path(repository=repository)


def _docker_hub_path(*, repository: str) -> str:
    if "/" in repository:
        return repository

    return f"library/{repository}"


def _docker_hub_tags(*, repository_path: str) -> tuple[str, ...]:
    url = f"https://hub.docker.com/v2/repositories/{repository_path}/tags?page_size=100"
    tags: list[str] = []
    for _ in range(_MAX_REGISTRY_PAGES):
        response = _json_response(url=url)
        if response is None or not isinstance(response.payload, dict):
            break

        tags.extend(_tag_names_from_docker_hub_payload(payload=response.payload))
        next_url = response.payload.get("next")
        if not isinstance(next_url, str) or not next_url:
            break

        url = next_url

    return tuple(tags)


def _tag_names_from_docker_hub_payload(*, payload: dict[str, Any]) -> tuple[str, ...]:
    results = payload.get("results", [])
    if not isinstance(results, list):
        return ()

    return tuple(
        tag_name
        for result in results
        if isinstance(result, dict)
        for tag_name in [result.get("name")]
        if isinstance(tag_name, str)
    )


def _ghcr_tags(*, repository_path: str) -> tuple[str, ...]:
    token = _ghcr_token(repository_path=repository_path)
    if token is None:
        return ()

    url = f"https://ghcr.io/v2/{repository_path}/tags/list?n=1000"
    tags: list[str] = []
    for _ in range(_MAX_REGISTRY_PAGES):
        response = _json_response(url=url, headers={"Authorization": f"Bearer {token}"})
        if response is None or not isinstance(response.payload, dict):
            break

        tags.extend(_tag_names_from_registry_payload(payload=response.payload))
        next_url = _next_ghcr_url(link=response.link)
        if next_url is None:
            break

        url = next_url

    return tuple(tags)


def _ghcr_token(*, repository_path: str) -> str | None:
    token_url = "https://ghcr.io/token?" + urllib.parse.urlencode(
        {"service": "ghcr.io", "scope": f"repository:{repository_path}:pull"},
    )
    response = _json_response(url=token_url)
    if response is None or not isinstance(response.payload, dict):
        return None

    token = response.payload.get("token")
    if not isinstance(token, str):
        return None

    return token


def _tag_names_from_registry_payload(*, payload: dict[str, Any]) -> tuple[str, ...]:
    tags = payload.get("tags", [])
    if not isinstance(tags, list):
        return ()

    return tuple(tag for tag in tags if isinstance(tag, str))


def _next_ghcr_url(*, link: str | None) -> str | None:
    if link is None:
        return None

    match = _GHCR_NEXT_LINK_RE.search(link)
    if match is None:
        return None

    url = match.group("url")
    if url.startswith("/"):
        return f"https://ghcr.io{url}"

    return url


def _best_compatible_container_tag(
    *,
    repository: str,
    current_tag: str,
    tags: tuple[str, ...],
) -> str | None:
    versioned_match = _best_same_variant_container_tag(
        repository=repository,
        current_tag=current_tag,
        tags=tags,
    )
    if versioned_match is not None and versioned_match != current_tag:
        return versioned_match

    pinned_floating_match = _best_pinned_floating_container_tag(
        current_tag=current_tag,
        tags=tags,
    )
    if pinned_floating_match is not None and pinned_floating_match != current_tag:
        return pinned_floating_match

    return None


def _best_same_variant_container_tag(
    *,
    repository: str,
    current_tag: str,
    tags: tuple[str, ...],
) -> str | None:
    current_version = _container_tag_version(tag=current_tag)
    if current_version is None:
        return None

    version_prefix = _required_container_version_prefix(
        repository=repository,
        current_tag=current_tag,
        version=current_version.version,
    )
    candidates = tuple(
        tag
        for tag in tags
        if _matches_container_tag_variant(
            tag=tag,
            current_version=current_version,
            version_prefix=version_prefix,
        )
    )
    return _best_ranked_container_tag(tags=candidates)


def _required_container_version_prefix(
    *,
    repository: str,
    current_tag: str,
    version: tuple[int, ...],
) -> tuple[int, ...]:
    if (
        _is_python_runtime_repository(repository=repository)
        and len(version) >= _PYTHON_VERSION_PREFIX_LENGTH
    ):
        return version[:_PYTHON_VERSION_PREFIX_LENGTH]

    if current_tag.startswith("python") and len(version) >= _PYTHON_VERSION_PREFIX_LENGTH:
        return version[:_PYTHON_VERSION_PREFIX_LENGTH]

    return version[:1]


def _is_python_runtime_repository(*, repository: str) -> bool:
    return repository in {"python", "library/python", "docker.io/library/python"}


def _matches_container_tag_variant(
    *,
    tag: str,
    current_version: ContainerTagVersion,
    version_prefix: tuple[int, ...],
) -> bool:
    candidate_version = _container_tag_version(tag=tag)
    if candidate_version is None:
        return False

    return (
        candidate_version.prefix == current_version.prefix
        and candidate_version.suffix == current_version.suffix
        and candidate_version.version[: len(version_prefix)] == version_prefix
    )


def _best_pinned_floating_container_tag(
    *,
    current_tag: str,
    tags: tuple[str, ...],
) -> str | None:
    suffix = f"-{current_tag}"
    return _best_ranked_container_tag(
        tags=tuple(tag for tag in tags if tag.endswith(suffix)),
    )


def _best_ranked_container_tag(*, tags: tuple[str, ...]) -> str | None:
    best_tag: str | None = None
    best_rank: tuple[int, tuple[int, ...], int] | None = None
    for tag in tags:
        rank = _container_tag_rank(tag=tag)
        if rank is None:
            continue

        if best_rank is None or rank > best_rank:
            best_tag = tag
            best_rank = rank

    return best_tag


def _container_tag_rank(*, tag: str) -> tuple[int, tuple[int, ...], int] | None:
    release_rank = _release_container_tag_rank(tag=tag)
    if release_rank is not None:
        return release_rank

    version = _container_tag_version(tag=tag)
    if version is None:
        return None

    return (
        1,
        _container_version_with_build_suffix(version=version),
        _suffix_preference(version.suffix),
    )


def _release_container_tag_rank(*, tag: str) -> tuple[int, tuple[int, ...], int] | None:
    match = _RELEASE_TAG_RE.match(tag)
    if match is None:
        return None

    release_key = tuple(
        int(part) for part in (*match.group("date").split("-"), *match.group("time").split("-"))
    )
    return 2, release_key, _suffix_preference(match.group("suffix"))


def _container_tag_version(*, tag: str) -> ContainerTagVersion | None:
    match = _CONTAINER_VERSION_RE.match(tag)
    if match is None:
        return None

    version = _container_version_key(version=match.group("version"))
    if version is None:
        return None

    return ContainerTagVersion(
        prefix=match.group("prefix"),
        version=version,
        suffix=match.group("suffix"),
    )


def _container_version_key(*, version: str) -> tuple[int, ...] | None:
    normalized_version = version.removeprefix("v")
    match = _VERSION_PREFIX_RE.match(normalized_version)
    if match is None:
        return None

    return tuple(int(part) for part in match.group("release").split("."))


def _container_version_with_build_suffix(*, version: ContainerTagVersion) -> tuple[int, ...]:
    build_match = _CONTAINER_BUILD_SUFFIX_RE.fullmatch(version.suffix)
    if build_match is None:
        return version.version

    return (*version.version, int(build_match.group("build")))


def _suffix_preference(suffix: str) -> int:
    if not suffix or _CONTAINER_BUILD_SUFFIX_RE.fullmatch(suffix):
        return 3

    return 2


def _major_version(*, ref: str) -> int | None:
    match = _MAJOR_REF_RE.match(ref)
    if match is None:
        return None

    return int(match.group("major"))


def _canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _latest_pypi_version(package_name: str) -> str | None:
    url = f"https://pypi.org/pypi/{package_name}/json"
    response = _json_response(url=url)
    if response is None or not isinstance(response.payload, dict):
        return None

    info = response.payload.get("info", {})
    if not isinstance(info, dict):
        return None

    return cast(str | None, info.get("version"))


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


def _json_response(*, url: str, headers: dict[str, str] | None = None) -> JsonResponse | None:
    if urllib.parse.urlparse(url).scheme != "https":
        return None

    request = urllib.request.Request(  # noqa: S310
        url,
        headers=headers or {},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            return JsonResponse(
                payload=json.load(response),
                link=response.headers.get("Link"),
            )
    except (
        OSError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ):
        return None


def _run_command(command: Sequence[str], *, repo_root: Path) -> None:
    subprocess.run(command, cwd=repo_root, check=True)  # noqa: S603


def _print_summary(*, summary: UpdateSummary, dry_run: bool) -> None:
    prefix = "Would update" if dry_run else "Updated"

    if (
        not summary.dependency_updates
        and not summary.action_updates
        and not summary.container_updates
    ):
        _write_line("No dependency, GitHub Action, or container image updates found.")
        return

    if summary.dependency_updates:
        _write_line(f"{prefix} pyproject.toml dependencies:")
        for dependency_update in summary.dependency_updates:
            _write_line(
                f"  {dependency_update.old_requirement} -> {dependency_update.new_requirement}",
            )

    if summary.action_updates:
        _write_line(f"{prefix} GitHub Action pins:")
        for action_update in summary.action_updates:
            relative_path = action_update.file_path.as_posix()
            _write_line(
                f"  {relative_path}: "
                f"{action_update.repository}@{action_update.old_ref} -> {action_update.new_ref}",
            )

    if summary.container_updates:
        _write_line(f"{prefix} container image pins:")
        for container_update in summary.container_updates:
            relative_path = container_update.file_path.as_posix()
            _write_line(
                f"  {relative_path}: {container_update.old_ref} -> {container_update.new_ref}",
            )


def _write_line(message: str) -> None:
    sys.stdout.write(f"{message}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
