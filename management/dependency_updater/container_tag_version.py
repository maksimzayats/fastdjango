from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class ContainerTagVersion:
    """Describe parsed version information from a container tag."""

    prefix: str
    version: tuple[int, ...]
    suffix: str
