"""Tests for generic agent thread runtime and harness integration."""

from __future__ import annotations

from pathlib import Path

from app.agents.runtime import AgentThreadRuntime
from app.agents.sandbox import LocalThreadSandboxProvider
from app.harness.engine import HarnessEngine
from app.harness.models import HarnessConstraints
from app.harness.state import HarnessMemoryStore


def test_agent_thread_runtime_creates_workspace_and_artifact(tmp_path: Path) -> None:
    runtime = AgentThreadRuntime(tmp_path / "threads")
    thread = runtime.create_thread(title="General Agent Thread", agent_name="ResearchAgent")

    assert thread["thread_id"]
    assert Path(thread["workspace"]["workspace"]).exists()
    assert Path(thread["workspace"]["uploads"]).exists()
    assert Path(thread["workspace"]["outputs"]).exists()

    runtime.append_message(thread["thread_id"], "user", "Investigate rollout blockers.")
    artifact = runtime.write_artifact(
        thread["thread_id"],
        name="summary.md",
        content="# Summary\n",
        kind="report",
        content_type="text/markdown",
        summary="unit test report",
    )
    loaded = runtime.load_thread(thread["thread_id"])

    assert artifact["relative_path"] == "outputs/summary.md"
    assert loaded
    assert loaded["message_count"] == 1
    assert loaded["artifact_count"] == 1


def test_agent_thread_runtime_executes_task_graph_with_pause_resume_and_retry(tmp_path: Path) -> None:
    runtime = AgentThreadRuntime(tmp_path / "threads")
    thread = runtime.create_thread(title="Graph Runtime Thread")
    graph = {
        "graph_id": "unit-graph",
        "nodes": [
            {"node_id": "scope", "title": "Scope", "node_type": "routing", "status": "ready", "depends_on": [], "commands": [], "notes": [], "artifacts": [], "metrics": {}},
            {"node_id": "evidence", "title": "Evidence", "node_type": "evidence", "status": "ready", "depends_on": ["scope"], "commands": [], "notes": [], "artifacts": [], "metrics": {"record_count": 2}},
            {"node_id": "review", "title": "Review", "node_type": "review", "status": "ready", "depends_on": ["evidence"], "commands": [], "notes": [], "artifacts": [], "metrics": {}},
        ],
    }

    paused = runtime.execute_task_graph(thread["thread_id"], graph=graph, execution_label="unit", max_nodes=1)
    assert paused["status"] == "paused"
    assert paused["graph"]["nodes"][0]["status"] == "completed"

    resumed = runtime.resume_execution(thread["thread_id"], paused["execution_id"])
    assert resumed["status"] == "completed"
    assert all(node["status"] == "completed" for node in resumed["graph"]["nodes"])

    retried = runtime.retry_execution(thread["thread_id"], resumed["execution_id"], from_node_id="evidence")
    assert retried["status"] == "completed"
    assert retried["parent_execution_id"] == resumed["execution_id"]


def test_agent_thread_runtime_interrupts_execution_and_uses_thread_workspace(tmp_path: Path) -> None:
    runtime = AgentThreadRuntime(tmp_path / "threads", sandbox_provider=LocalThreadSandboxProvider())
    thread = runtime.create_thread(title="Interruptible Thread")
    graph = {
        "graph_id": "interrupt-graph",
        "nodes": [
            {"node_id": "scope", "title": "Scope", "node_type": "routing", "status": "ready", "depends_on": [], "commands": [], "notes": [], "artifacts": [], "metrics": {}},
            {"node_id": "package", "title": "Package", "node_type": "packaging", "status": "ready", "depends_on": ["scope"], "commands": [], "notes": [], "artifacts": [], "metrics": {}},
        ],
    }

    runtime.request_interrupt(thread["thread_id"], reason="manual-test")
    interrupted = runtime.execute_task_graph(thread["thread_id"], graph=graph, execution_label="interrupt")
    persisted = runtime.load_thread(thread["thread_id"])

    assert interrupted["status"] == "interrupted"
    assert persisted
    assert persisted["status"] == "interrupted"
    assert persisted["control"]["interrupt_requested"] is True

    runtime.clear_interrupt(thread["thread_id"])
    resumed = runtime.resume_execution(thread["thread_id"], interrupted["execution_id"])
    sandbox = runtime.sandbox_provider.get(tmp_path / "threads" / thread["thread_id"])
    output_files = sandbox.list_files("outputs")

    assert resumed["status"] == "completed"
    assert any(path.endswith("scope.json") for path in output_files)
    assert any(path.endswith("package.json") for path in output_files)


def test_harness_run_can_persist_into_thread_runtime(tmp_path: Path) -> None:
    engine = HarnessEngine()
    engine.thread_runtime = AgentThreadRuntime(tmp_path / "threads")
    engine.memory = HarnessMemoryStore(tmp_path / "memory.json")

    thread = engine.create_thread(title="Persistent Execution Thread")
    run = engine.run(
        query="Design an implementation roadmap with migration risks and validation gates.",
        constraints=HarnessConstraints(max_steps=3, max_tool_calls=3),
        thread_id=thread["thread_id"],
    )
    persisted = engine.get_thread(thread["thread_id"])

    assert run.metadata.get("thread", {}).get("thread_id") == thread["thread_id"]
    assert persisted
    assert persisted["latest_query"] == run.query
    assert persisted["message_count"] >= 2
    assert persisted["artifact_count"] >= 3
    assert persisted["runs"][-1]["mission_type"] == "implementation_pack"
    assert any(item["kind"] == "mission_pack" for item in persisted["artifacts"])


def test_harness_engine_can_execute_mission_graph_inside_thread(tmp_path: Path) -> None:
    engine = HarnessEngine()
    engine.thread_runtime = AgentThreadRuntime(tmp_path / "threads")
    engine.memory = HarnessMemoryStore(tmp_path / "memory.json")

    thread = engine.create_thread(title="Mission Execution Thread")
    run = engine.run(
        query="Create a practical execution plan with risks and measurable checkpoints.",
        constraints=HarnessConstraints(max_steps=3, max_tool_calls=3),
        thread_id=thread["thread_id"],
    )
    execution = engine.execute_thread_task_graph(
        thread["thread_id"],
        run.mission["task_graph"],
        execution_label=run.mission["name"],
        context={"mission": run.mission},
    )
    persisted = engine.get_thread(thread["thread_id"])

    assert execution["status"] == "completed"
    assert persisted
    assert persisted["executions"][-1]["execution_id"] == execution["execution_id"]
    assert any(item["kind"].endswith("_artifact") for item in persisted["artifacts"])
