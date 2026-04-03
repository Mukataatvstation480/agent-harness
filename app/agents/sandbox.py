"""Thread-bound sandbox/provider abstraction for generic agent runtime."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
from urllib import parse, request


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


@dataclass(frozen=True)
class RemoteSandboxConfig:
    """Configuration for strict remote sandbox access."""

    base_url: str
    api_key: str = ""
    timeout_seconds: int = 20
    require_https: bool = True
    allowed_areas: tuple[str, ...] = ("workspace", "uploads", "outputs")


class RemoteThreadSandbox(ThreadSandbox):
    """HTTP-backed sandbox for one thread with strict path validation."""

    def __init__(self, thread_root: Path, config: RemoteSandboxConfig) -> None:
        self.thread_root = thread_root
        self.thread_id = thread_root.name
        self.config = config
        parsed = parse.urlparse(config.base_url)
        if config.require_https and parsed.scheme != "https":
            raise ValueError("remote sandbox requires https base_url")
        if not parsed.netloc:
            raise ValueError("remote sandbox base_url is invalid")

    def workspace_paths(self) -> dict[str, str]:
        payload = self._request_json("GET", f"/threads/{self.thread_id}/workspace")
        return {
            "root": str(payload.get("root", "")),
            "workspace": str(payload.get("workspace", "")),
            "uploads": str(payload.get("uploads", "")),
            "outputs": str(payload.get("outputs", "")),
        }

    def write_text(self, relative_path: str, content: str, area: str = "outputs") -> Path:
        safe_area = self._validate_area(area)
        safe_path = self._validate_relative_path(relative_path)
        payload = self._request_json(
            "POST",
            f"/threads/{self.thread_id}/write_text",
            {
                "area": safe_area,
                "relative_path": safe_path,
                "content": content,
            },
        )
        return Path(str(payload.get("path", f"{self.thread_id}/{safe_area}/{safe_path}")))

    def read_text(self, relative_path: str, area: str = "workspace") -> str:
        safe_area = self._validate_area(area)
        safe_path = self._validate_relative_path(relative_path)
        payload = self._request_json(
            "POST",
            f"/threads/{self.thread_id}/read_text",
            {
                "area": safe_area,
                "relative_path": safe_path,
            },
        )
        return str(payload.get("content", ""))

    def list_files(self, area: str = "workspace") -> list[str]:
        safe_area = self._validate_area(area)
        payload = self._request_json("GET", f"/threads/{self.thread_id}/list_files?area={parse.quote(safe_area)}")
        files = payload.get("files", [])
        return [str(item) for item in files if str(item)]

    def execute_command(self, command: str, area: str = "workspace", timeout_seconds: int = 30) -> SandboxCommandResult:
        safe_area = self._validate_area(area)
        payload = self._request_json(
            "POST",
            f"/threads/{self.thread_id}/execute_command",
            {
                "area": safe_area,
                "command": command,
                "timeout_seconds": max(1, timeout_seconds),
            },
        )
        return SandboxCommandResult(
            command=str(payload.get("command", command)),
            exit_code=int(payload.get("exit_code", 0)),
            stdout=str(payload.get("stdout", "")),
            stderr=str(payload.get("stderr", "")),
            duration_ms=float(payload.get("duration_ms", 0.0)),
        )

    def _validate_area(self, area: str) -> str:
        if area not in self.config.allowed_areas:
            raise ValueError(f"remote sandbox area not allowed: {area}")
        return area

    @staticmethod
    def _validate_relative_path(relative_path: str) -> str:
        candidate = relative_path.replace("\\", "/").strip("/")
        if not candidate:
            raise ValueError("relative_path must not be empty")
        if ".." in candidate.split("/"):
            raise ValueError("relative_path escapes sandbox")
        return candidate

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}{path}"
        data = None
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, headers=headers, method=method)
        with request.urlopen(req, timeout=max(1, self.config.timeout_seconds)) as response:
            return json.loads(response.read().decode("utf-8"))


class RemoteThreadSandboxProvider(ThreadSandboxProvider):
    """Strict HTTP-backed sandbox provider."""

    def __init__(self, config: RemoteSandboxConfig) -> None:
        self.config = config

    def get(self, thread_root: Path) -> ThreadSandbox:
        return RemoteThreadSandbox(thread_root, self.config)
