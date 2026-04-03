"""Thread-bound sandbox/provider abstraction for generic agent runtime."""

from __future__ import annotations

import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SandboxCommandResult:
    """Result of one sandbox command invocation."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": round(self.duration_ms, 2),
        }


class ThreadSandbox(ABC):
    """Abstract sandbox scoped to one thread workspace."""

    @abstractmethod
    def workspace_paths(self) -> dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def write_text(self, relative_path: str, content: str, area: str = "outputs") -> Path:
        raise NotImplementedError

    @abstractmethod
    def read_text(self, relative_path: str, area: str = "workspace") -> str:
        raise NotImplementedError

    @abstractmethod
    def list_files(self, area: str = "workspace") -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def execute_command(self, command: str, area: str = "workspace", timeout_seconds: int = 30) -> SandboxCommandResult:
        raise NotImplementedError


class LocalThreadSandbox(ThreadSandbox):
    """Local filesystem-backed sandbox for one thread."""

    def __init__(self, thread_root: Path) -> None:
        self.thread_root = thread_root.resolve()
        self.thread_root.mkdir(parents=True, exist_ok=True)
        for name in ("workspace", "uploads", "outputs"):
            (self.thread_root / name).mkdir(parents=True, exist_ok=True)

    def workspace_paths(self) -> dict[str, str]:
        return {
            "root": str(self.thread_root),
            "workspace": str(self.thread_root / "workspace"),
            "uploads": str(self.thread_root / "uploads"),
            "outputs": str(self.thread_root / "outputs"),
        }

    def write_text(self, relative_path: str, content: str, area: str = "outputs") -> Path:
        target = self._resolve(area, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def read_text(self, relative_path: str, area: str = "workspace") -> str:
        target = self._resolve(area, relative_path)
        return target.read_text(encoding="utf-8")

    def list_files(self, area: str = "workspace") -> list[str]:
        base = self._resolve(area, "")
        if not base.exists():
            return []
        return [
            path.relative_to(base).as_posix()
            for path in sorted(base.rglob("*"))
            if path.is_file()
        ]

    def execute_command(self, command: str, area: str = "workspace", timeout_seconds: int = 30) -> SandboxCommandResult:
        cwd = self._resolve(area, "")
        start = time.perf_counter()
        proc = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=max(1, timeout_seconds),
            check=False,
        )
        duration_ms = (time.perf_counter() - start) * 1000.0
        return SandboxCommandResult(
            command=command,
            exit_code=int(proc.returncode),
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_ms=duration_ms,
        )

    def _resolve(self, area: str, relative_path: str) -> Path:
        allowed = {"root", "workspace", "uploads", "outputs"}
        key = area if area in allowed else "workspace"
        base = self.thread_root if key == "root" else self.thread_root / key
        target = (base / relative_path).resolve()
        if target != base and base not in target.parents:
            raise ValueError(f"path escapes sandbox: {relative_path}")
        return target


class ThreadSandboxProvider(ABC):
    """Abstract provider that returns a sandbox for one thread."""

    @abstractmethod
    def get(self, thread_root: Path) -> ThreadSandbox:
        raise NotImplementedError


class LocalThreadSandboxProvider(ThreadSandboxProvider):
    """Local filesystem-backed provider."""

    def get(self, thread_root: Path) -> ThreadSandbox:
        return LocalThreadSandbox(thread_root)
