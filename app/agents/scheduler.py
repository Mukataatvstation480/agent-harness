"""Recovery-oriented scheduler helpers for long-running thread executions."""

from __future__ import annotations

from typing import Any

from app.agents.runtime import AgentThreadRuntime


class AgentExecutionScheduler:
    """Inspect and recover incomplete thread executions."""

    def __init__(self, runtime: AgentThreadRuntime) -> None:
        self.runtime = runtime

    def list_recoverable(self, limit: int = 50) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for thread in self.runtime.list_threads(limit=limit):
            payload = self.runtime.load_thread(str(thread.get("thread_id", ""))) or {}
            for execution in payload.get("executions", []):
                status = str(execution.get("status", ""))
                if status not in {"queued", "running", "paused", "interrupted"}:
                    continue
                rows.append(
                    {
                        "thread_id": payload.get("thread_id", ""),
                        "execution_id": execution.get("execution_id", ""),
                        "label": execution.get("label", ""),
                        "status": status,
                        "recommended_action": "resume" if status in {"paused", "interrupted"} else "recover_async",
                    }
                )
        return rows[:limit]

    def recover_execution(
        self,
        thread_id: str,
        execution_id: str,
        *,
        async_mode: bool = True,
    ) -> dict[str, Any]:
        payload = self.runtime.load_thread(thread_id) or self.runtime.ensure_thread(thread_id)
        target = None
        for execution in payload.get("executions", []):
            if str(execution.get("execution_id", "")) == execution_id:
                target = execution
                break
        if target is None:
            raise ValueError(f"unknown execution: {execution_id}")

        graph = target.get("graph", {}) if isinstance(target.get("graph", {}), dict) else {}
        for node in graph.get("nodes", []):
            if str(node.get("status", "")) == "running":
                node["status"] = "ready"
        target["graph"] = graph
        target["status"] = "paused"
        self.runtime.clear_interrupt(thread_id)
        if async_mode:
            refreshed = self.runtime.start_task_graph_async(
                thread_id,
                graph=graph,
                execution_label=str(target.get("label", "")),
                execution_id=execution_id,
            )
            current = refreshed.get("executions", [])[-1] if refreshed.get("executions") else target
            return current
        return self.runtime.resume_execution(thread_id, execution_id)

    def recover_all(self, *, async_mode: bool = True, limit: int = 50) -> dict[str, Any]:
        recovered: list[dict[str, Any]] = []
        for item in self.list_recoverable(limit=limit):
            recovered.append(
                self.recover_execution(
                    str(item.get("thread_id", "")),
                    str(item.get("execution_id", "")),
                    async_mode=async_mode,
                )
            )
        return {
            "schema": "agent-harness-recovery-scheduler/v1",
            "recovered": recovered,
            "count": len(recovered),
        }
