"""Harness memory/context state manager."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "harness_memory.json"


def _default_payload() -> dict[str, Any]:
    return {"sessions": {}}


class HarnessMemoryStore:
    """Simple persistent memory store keyed by session id."""

    def __init__(self, file_path: Path | None = None) -> None:
        self._file = file_path or DATA_FILE
        self._ensure()

    def _ensure(self) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        if not self._file.exists():
            self._file.write_text(json.dumps(_default_payload(), indent=2), encoding="utf-8")

    def _load(self) -> dict[str, Any]:
        self._ensure()
        try:
            payload = json.loads(self._file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = _default_payload()
            self._save(payload)
            return payload

        if not isinstance(payload, dict):
            payload = _default_payload()
        payload.setdefault("sessions", {})
        return payload

    def _save(self, payload: dict[str, Any]) -> None:
        self._file.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def append_event(self, session_id: str, event: dict[str, Any]) -> None:
        """Append one event into session memory."""

        payload = self._load()
        sessions = payload.setdefault("sessions", {})
        events = sessions.setdefault(session_id, [])
        events.append(event)
        self._save(payload)

    def read_recent(self, session_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Read recent memory events for a session."""

        payload = self._load()
        events = payload.get("sessions", {}).get(session_id, [])
        return events[-limit:]

    def snapshot(self) -> dict[str, Any]:
        """Return full-memory snapshot for reproducible experiments."""

        return self._load()

    def restore(self, payload: dict[str, Any]) -> None:
        """Restore memory snapshot."""

        self._save(payload)

    def clear(self) -> None:
        """Clear all sessions from memory store."""

        self._save(_default_payload())
