from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from management.setup_wizard.models import FileOperation


@dataclass(kw_only=True)
class FilePlan:
    repo_root: Path
    operations: list[FileOperation] = field(default_factory=list)

    def add_write(self, path: Path, *, content: str, detail: str) -> None:
        existing_content = path.read_text(encoding="utf-8") if path.exists() else None
        if existing_content == content:
            return

        self.operations.append(
            FileOperation(
                kind="write",
                path=path,
                detail=detail,
                content=content,
            ),
        )

    def add_delete(self, path: Path, *, detail: str, exists_path: Path | None = None) -> None:
        check_path = exists_path or path
        if not check_path.exists():
            return

        self.operations.append(
            FileOperation(
                kind="delete",
                path=path,
                detail=detail,
            ),
        )

    def add_rename(self, source_path: Path, target_path: Path, *, detail: str) -> None:
        if source_path == target_path or not source_path.exists():
            return

        self.operations.append(
            FileOperation(
                kind="rename",
                path=source_path,
                target_path=target_path,
                detail=detail,
            ),
        )

    def add_command(self, command: tuple[str, ...], *, detail: str) -> None:
        self.operations.append(
            FileOperation(
                kind="command",
                path=self.repo_root,
                command=command,
                detail=detail,
            ),
        )

    def apply(self, *, run_commands: bool = True) -> None:
        for operation in self.operations:
            if operation.kind == "rename":
                self._apply_rename(operation=operation)
            elif operation.kind == "delete":
                self._apply_delete(operation=operation)
            elif operation.kind == "write":
                self._apply_write(operation=operation)
            elif run_commands:
                self._apply_command(operation=operation)

    def relative_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.repo_root).as_posix()
        except ValueError:
            return path.as_posix()

    def _apply_rename(self, *, operation: FileOperation) -> None:
        if operation.target_path is None:
            msg = "Rename operation is missing a target path."
            raise ValueError(msg)

        operation.target_path.parent.mkdir(parents=True, exist_ok=True)
        operation.path.rename(operation.target_path)

    def _apply_delete(self, *, operation: FileOperation) -> None:
        if operation.path.is_dir():
            shutil.rmtree(operation.path)
            return

        operation.path.unlink()

    def _apply_write(self, *, operation: FileOperation) -> None:
        if operation.content is None:
            msg = "Write operation is missing content."
            raise ValueError(msg)

        operation.path.parent.mkdir(parents=True, exist_ok=True)
        operation.path.write_text(operation.content, encoding="utf-8")

    def _apply_command(self, *, operation: FileOperation) -> None:
        if operation.command is None:
            msg = "Command operation is missing a command."
            raise ValueError(msg)

        subprocess.run(operation.command, cwd=self.repo_root, check=True)  # noqa: S603
