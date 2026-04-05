"""Executable task-graph protocol shared by mission packs and runtime artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TaskGraphArtifact:
    """One material artifact emitted or consumed by a task node."""

    kind: str
    label: str
    status: str
    path: str = ""
    summary: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "label": self.label,
            "status": self.status,
            "path": self.path,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class TaskGraphNode:
    """One executable node inside a mission-oriented task graph."""

    node_id: str
    title: str
    node_type: str
    status: str
    depends_on: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    artifacts: list[TaskGraphArtifact] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "title": self.title,
            "node_type": self.node_type,
            "status": self.status,
            "depends_on": list(self.depends_on),
            "commands": list(self.commands),
            "notes": list(self.notes),
            "artifacts": [item.to_dict() for item in self.artifacts],
            "metrics": dict(self.metrics),
        }


class ExecutableTaskGraph:
    """Task graph with lightweight execution semantics and artifact contracts."""

    SCHEMA = "agent-harness-executable-task-graph/v1"

    def __init__(
        self,
        *,
        graph_id: str,
        mission_type: str,
        query: str,
        nodes: list[TaskGraphNode],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.graph_id = graph_id
        self.mission_type = mission_type
        self.query = query
        self.nodes = nodes
        self.metadata = dict(metadata or {})

    def to_dict(self) -> dict[str, Any]:
        completed = sum(1 for node in self.nodes if node.status == "completed")
        runnable = [
            node.node_id
            for node in self.nodes
            if node.status in {"planned", "ready"}
            and all(parent.status == "completed" for parent in self._parents(node))
        ]
        return {
            "schema": self.SCHEMA,
            "graph_id": self.graph_id,
            "mission_type": self.mission_type,
            "query": self.query,
            "metadata": dict(self.metadata),
            "nodes": [item.to_dict() for item in self.nodes],
            "edges": self._edges(),
            "summary": {
                "node_count": len(self.nodes),
                "completed_nodes": completed,
                "completion_ratio": round(completed / max(len(self.nodes), 1), 4),
                "runnable_nodes": runnable,
                "critical_path": self._critical_path(),
                "phase_summary": self._phase_summary(),
            },
        }

    def _edges(self) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        for node in self.nodes:
            for parent in node.depends_on:
                rows.append({"from": parent, "to": node.node_id})
        return rows

    def _parents(self, node: TaskGraphNode) -> list[TaskGraphNode]:
        wanted = set(node.depends_on)
        return [item for item in self.nodes if item.node_id in wanted]

    def _critical_path(self) -> list[str]:
        by_id = {item.node_id: item for item in self.nodes}
        memo: dict[str, list[str]] = {}

        def walk(node_id: str) -> list[str]:
            if node_id in memo:
                return memo[node_id]
            node = by_id[node_id]
            if not node.depends_on:
                memo[node_id] = [node_id]
                return memo[node_id]
            parent_paths = [walk(parent_id) for parent_id in node.depends_on if parent_id in by_id]
            best = max(parent_paths, key=len) if parent_paths else []
            memo[node_id] = [*best, node_id]
            return memo[node_id]

        if not self.nodes:
            return []
        best_path = max((walk(node.node_id) for node in self.nodes), key=len, default=[])
        return best_path

    def _phase_summary(self) -> list[dict[str, Any]]:
        phases: dict[str, dict[str, Any]] = {}
        order = {"observe": 0, "decide": 1, "act": 2, "deliver": 3}
        for node in self.nodes:
            metrics = node.metrics if isinstance(node.metrics, dict) else {}
            phase = str(metrics.get("loop_phase", "")).strip() or "act"
            bucket = phases.setdefault(
                phase,
                {
                    "phase": phase,
                    "node_count": 0,
                    "completed_nodes": 0,
                    "nodes": [],
                },
            )
            bucket["node_count"] += 1
            if node.status == "completed":
                bucket["completed_nodes"] += 1
            bucket["nodes"].append(node.node_id)
        rows = list(phases.values())
        rows.sort(key=lambda item: order.get(str(item.get("phase", "")), 99))
        for item in rows:
            node_count = max(int(item.get("node_count", 0)), 1)
            item["completion_ratio"] = round(int(item.get("completed_nodes", 0)) / node_count, 4)
        return rows
