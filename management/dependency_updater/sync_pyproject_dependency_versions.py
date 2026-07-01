import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from management.dependency_updater.dependency_update import DependencyUpdate
from management.dependency_updater.http import _json_response

_VersionResolver = Callable[[str], str | None]

_NAME_RE = re.compile(r"(?P<name>[A-Za-z0-9_.-]+)(?P<extras>\[[^\]]+\])?")
_LOWER_BOUND_RE = re.compile(r"(?P<operator>>=|>)\s*[^,; ]+")
_UPPER_BOUND_RE = re.compile(r"(?:^|,)\s*(?P<operator><=|<)\s*(?P<version>[^,; ]+)")
_VERSION_PREFIX_RE = re.compile(r"(?P<release>\d+(?:\.\d+)*)")


def sync_pyproject_dependency_versions(
    *,
    repo_root: Path,
    dry_run: bool = False,
    latest_version_resolver: _VersionResolver | None = None,
) -> tuple[DependencyUpdate, ...]:
    """Sync pyproject dependency lower bounds from uv.lock or PyPI.

    Args:
        repo_root: Repository root containing `pyproject.toml` and `uv.lock`.
        dry_run: Whether to return updates without writing `pyproject.toml`.
        latest_version_resolver: Optional resolver used by tests or custom runs.

    Returns:
        Dependency updates that were applied or planned.

    Raises:
        RuntimeError: If a dependency requirement cannot be found in pyproject text.
    """
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
    latest_version_resolver: _VersionResolver,
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


def _canonical_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _latest_pypi_version(package_name: str) -> str | None:
    url = f"https://pypi.org/pypi/{package_name}/json"
    response = _json_response(url=url)
    if response is None or not isinstance(response.payload, dict):
        return None

    package_info = response.payload.get("info", {})
    if not isinstance(package_info, dict):
        return None

    return cast(str | None, package_info.get("version"))
