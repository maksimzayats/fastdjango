from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, kw_only=True)
class ActionUpdate:
    """Describe a GitHub Action version update."""

    file_path: Path
    repository: str
    old_ref: str
    new_ref: str
