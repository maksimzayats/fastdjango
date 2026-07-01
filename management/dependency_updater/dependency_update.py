from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class DependencyUpdate:
    """Describe a Python dependency version update."""

    old_requirement: str
    new_requirement: str
