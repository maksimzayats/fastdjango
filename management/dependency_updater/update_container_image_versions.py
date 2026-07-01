import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from management.dependency_updater.container_image import ContainerImage
from management.dependency_updater.container_image_reference import ContainerImageReference
from management.dependency_updater.container_image_update import ContainerImageUpdate
from management.dependency_updater.container_tag_version import ContainerTagVersion
from management.dependency_updater.http import _json_response
from management.dependency_updater.parallel import _resolve_in_parallel

_ContainerTagResolver = Callable[[str, str | None], str | None]

_COMPOSE_IMAGE_RE = re.compile(
    r"^(?P<prefix>\s*image:\s*[\"']?)(?P<image>[^\s\"']+)(?P<suffix>[\"']?\s*(?:#.*)?)$",
    re.MULTILINE,
)
_DOCKER_FROM_RE = re.compile(
    r"^(?P<prefix>\s*FROM\s+(?:--platform=\S+\s+)?)(?P<image>[^\s]+)(?P<suffix>.*)$",
    re.IGNORECASE | re.MULTILINE,
)
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
_CONTAINER_REFERENCE_SUFFIXES = frozenset((".md", ".yaml", ".yml"))
_DOCKER_IO_REGISTRY = "docker.io"
_MAX_REGISTRY_PAGES = 20
_PYTHON_VERSION_PREFIX_LENGTH = 2


def update_container_image_versions(
    *,
    repo_root: Path,
    dry_run: bool = False,
    latest_tag_resolver: _ContainerTagResolver | None = None,
) -> tuple[ContainerImageUpdate, ...]:
    """Update Docker and Compose image references.

    Args:
        repo_root: Repository root containing Docker assets and documentation.
        dry_run: Whether to return updates without writing files.
        latest_tag_resolver: Optional resolver used by tests or custom runs.

    Returns:
        Container image updates that were applied or planned.
    """
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
    latest_tag_resolver: _ContainerTagResolver,
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
    latest_tag_resolver: _ContainerTagResolver,
) -> dict[tuple[str, str | None], str | None]:
    keys = tuple(sorted({(image.repository, image.tag) for image in images}))
    return _resolve_in_parallel(
        entries=keys,
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
    ordered_replacements = sorted(
        replacements.items(),
        key=_replacement_length,
        reverse=True,
    )
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
    if registry == _DOCKER_IO_REGISTRY:
        return _docker_hub_tags(repository_path=repository_path)

    if registry == "ghcr.io":
        return _ghcr_tags(repository_path=repository_path)

    return ()


def _container_registry_and_path(*, repository: str) -> tuple[str, str]:
    first_component, separator, remaining_path = repository.partition("/")
    if first_component == _DOCKER_IO_REGISTRY and separator:
        return _DOCKER_IO_REGISTRY, _docker_hub_path(repository=remaining_path)

    has_registry = (
        "." in first_component or ":" in first_component or first_component == "localhost"
    )
    if has_registry and separator:
        return first_component, remaining_path

    return _DOCKER_IO_REGISTRY, _docker_hub_path(repository=repository)


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
    payload_results = payload.get("results", [])
    if not isinstance(payload_results, list):
        return ()

    return tuple(
        tag_name
        for payload_result in payload_results
        if isinstance(payload_result, dict)
        for tag_name in _docker_hub_payload_tag_name(payload=payload_result)
        if isinstance(tag_name, str)
    )


def _docker_hub_payload_tag_name(*, payload: dict[str, Any]) -> tuple[object, ...]:
    return (payload.get("name"),)


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
    query = urlencode(
        {"service": "ghcr.io", "scope": f"repository:{repository_path}:pull"},
    )
    token_url = f"https://ghcr.io/token?{query}"
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
    return repository in {"python", "library/python", f"{_DOCKER_IO_REGISTRY}/library/python"}


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


def _replacement_length(replacement: tuple[str, str]) -> int:
    return len(replacement[0])
