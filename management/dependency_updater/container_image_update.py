from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, kw_only=True)
class ContainerImageUpdate:
    """Describe a container image version update."""

    file_path: Path
    old_ref: str
    new_ref: str
