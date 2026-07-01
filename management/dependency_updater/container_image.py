from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class ContainerImage:
    """Describe a container image reference."""

    repository: str
    tag: str | None
    digest: str | None
