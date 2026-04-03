"""Task-graph node to runtime-action mapper."""

from __future__ import annotations

import json
from typing import Any

from app.agents.sandbox import ThreadSandbox


class TaskGraphActionMapper:
    """Map generic task-graph nodes into thread-runtime actions."""

    def execute_node(
        self,
        *,
        sandbox: ThreadSandbox,
        execution_id: str,
        node: dict[str, Any],
        graph: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        node_id = str(node.get("node_id", "node"))
        node_type = str(node.get("node_type", "artifact"))
        body = self._render_payload(node=node, graph=graph, context=context)
        relative_path = f"executions/{execution_id}/{node_id}.json"
        target = sandbox.write_text(relative_path, json.dumps(body, indent=2, default=str), area="outputs")
        artifact = {
            "kind": f"{node_type}_artifact",
            "label": str(node.get("title", node_id)),
            "status": "completed",
            "path": str(target),
            "summary": body.get("summary", ""),
        }
        return {
            "node_id": node_id,
            "status": "completed",
            "artifact": artifact,
            "result": body,
        }

    @staticmethod
    def _render_payload(
        *,
        node: dict[str, Any],
        graph: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        node_type = str(node.get("node_type", "artifact"))
        metrics = node.get("metrics", {}) if isinstance(node.get("metrics", {}), dict) else {}
        title = str(node.get("title", ""))
        notes = list(node.get("notes", [])) if isinstance(node.get("notes", []), list) else []
        commands = list(node.get("commands", [])) if isinstance(node.get("commands", []), list) else []
        summary = title
        payload: dict[str, Any] = {
            "node_id": node.get("node_id", ""),
            "title": title,
            "node_type": node_type,
            "notes": notes,
            "commands": commands,
            "metrics": metrics,
            "context_keys": sorted(context.keys()),
            "graph_id": graph.get("graph_id", ""),
        }

        if node_type in {"routing", "framing"}:
            summary = f"routing framed with {metrics or 'default metrics'}"
        elif node_type == "evidence":
            summary = f"evidence staged with {metrics.get('record_count', 0)} records"
        elif node_type in {"synthesis", "packaging"}:
            summary = f"packaged {title.lower()}"
        elif node_type in {"evaluation", "review"}:
            summary = f"evaluation/review completed for {title.lower()}"
        elif node_type in {"execution_plan", "execution", "validation_plan"}:
            summary = f"execution plan contains {len(commands)} commands"
        payload["summary"] = summary
        return payload
