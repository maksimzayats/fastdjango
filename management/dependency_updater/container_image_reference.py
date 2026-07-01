from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, kw_only=True)
class ContainerImageReference:
    """Describe a file-local container image reference."""

    file_path: Path
    image_ref: str
