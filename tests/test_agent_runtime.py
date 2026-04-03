"""Tests for generic agent thread runtime and harness integration."""

from __future__ import annotations

import json
import time
from io import BytesIO
from pathlib import Path
from urllib import request

from app.agents.runtime import AgentThreadRuntime
from app.agents.sandbox import LocalThreadSandboxProvider, RemoteSandboxConfig, RemoteThreadSandboxProvider
from app.agents.scheduler import AgentExecutionScheduler
from app.agents.workspace_view import ThreadWorkspaceStreamBuilder
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


def test_agent_thread_runtime_supports_async_wait_and_interrupt(tmp_path: Path) -> None:
    runtime = AgentThreadRuntime(tmp_path / "threads")
    thread = runtime.create_thread(title="Async Runtime Thread")
    graph = {
        "graph_id": "async-graph",
        "nodes": [
            {
                "node_id": "slow_scope",
                "title": "Slow Scope",
                "node_type": "routing",
                "status": "ready",
                "depends_on": [],
                "commands": [],
                "notes": [],
                "artifacts": [],
                "metrics": {"delay_ms": 250},
            },
            {
                "node_id": "finalize",
                "title": "Finalize",
                "node_type": "review",
                "status": "ready",
                "depends_on": ["slow_scope"],
                "commands": [],
                "notes": [],
                "artifacts": [],
                "metrics": {"delay_ms": 250},
            },
        ],
    }

    queued = runtime.start_task_graph_async(thread["thread_id"], graph=graph, execution_label="async")
    execution_id = queued["executions"][-1]["execution_id"]
    waiting = runtime.wait_for_execution(thread["thread_id"], execution_id, timeout_seconds=0.01)
    runtime.request_interrupt(thread["thread_id"], reason="test-interrupt")
    interrupted = runtime.wait_for_execution(thread["thread_id"], execution_id, timeout_seconds=2.0)

    assert waiting["status"] in {"queued", "running", "waiting"}
    assert interrupted["status"] == "interrupted"
    assert interrupted["interrupt_reason"] == "test-interrupt"


def test_parallel_subagents_scheduler_and_workspace_view(tmp_path: Path) -> None:
    engine = HarnessEngine()
    engine.thread_runtime = AgentThreadRuntime(tmp_path / "threads")
    engine.memory = HarnessMemoryStore(tmp_path / "memory.json")
    engine.scheduler.runtime = engine.thread_runtime
    engine.subagents.runtime = engine.thread_runtime

    thread = engine.create_thread(title="Parallel Subagents Thread")
    run = engine.run(
        query="Create a cross-functional launch plan with evidence and execution tracks.",
        constraints=HarnessConstraints(max_steps=3, max_tool_calls=3),
        thread_id=thread["thread_id"],
    )
    subagents = [
        {
            "name": "ops",
            "graph": {
                "graph_id": "ops",
                "nodes": [
                    {"node_id": "scope_ops", "title": "Scope Ops", "node_type": "routing", "status": "ready", "depends_on": [], "commands": [], "notes": [], "artifacts": [], "metrics": {}},
                    {"node_id": "report_ops", "title": "Report Ops", "node_type": "review", "status": "ready", "depends_on": ["scope_ops"], "commands": [], "notes": [], "artifacts": [], "metrics": {}},
                ],
            },
            "context": {"mission": run.mission},
        },
        {
            "name": "risk",
            "graph": {
                "graph_id": "risk",
                "nodes": [
                    {"node_id": "scope_risk", "title": "Scope Risk", "node_type": "routing", "status": "ready", "depends_on": [], "commands": [], "notes": [], "artifacts": [], "metrics": {}},
                    {"node_id": "report_risk", "title": "Report Risk", "node_type": "review", "status": "ready", "depends_on": ["scope_risk"], "commands": [], "notes": [], "artifacts": [], "metrics": {}},
                ],
            },
            "context": {"mission": run.mission},
        },
    ]

    parallel = engine.run_parallel_subagents(thread["thread_id"], subagents, wait_timeout_seconds=5.0)
    stream = engine.build_thread_workspace_stream(thread["thread_id"])
    html = engine.render_thread_workspace_html(thread["thread_id"])

    assert parallel["summary"]["count"] == 2
    assert parallel["summary"]["completed"] == 2
    assert stream["schema"] == "agent-harness-workspace-stream/v1"
    assert len(stream["executions"]) >= 2
    assert "<html" in html.lower()


def test_scheduler_recovers_interrupted_execution(tmp_path: Path) -> None:
    runtime = AgentThreadRuntime(tmp_path / "threads")
    scheduler = AgentExecutionScheduler(runtime)
    thread = runtime.create_thread(title="Recovery Thread")
    graph = {
        "graph_id": "recoverable",
        "nodes": [
            {"node_id": "scope", "title": "Scope", "node_type": "routing", "status": "ready", "depends_on": [], "commands": [], "notes": [], "artifacts": [], "metrics": {"delay_ms": 200}},
            {"node_id": "report", "title": "Report", "node_type": "review", "status": "ready", "depends_on": ["scope"], "commands": [], "notes": [], "artifacts": [], "metrics": {"delay_ms": 200}},
        ],
    }

    queued = runtime.start_task_graph_async(thread["thread_id"], graph=graph, execution_label="recoverable")
    execution_id = queued["executions"][-1]["execution_id"]
    time.sleep(0.05)
    runtime.request_interrupt(thread["thread_id"], reason="recover-me")
    runtime.wait_for_execution(thread["thread_id"], execution_id, timeout_seconds=5.0)
    recoverable = scheduler.list_recoverable()
    recovered = scheduler.recover_execution(thread["thread_id"], execution_id, async_mode=False)

    assert any(item["execution_id"] == execution_id for item in recoverable)
    assert recovered["status"] == "completed"


def test_remote_thread_sandbox_provider_uses_http_contract(monkeypatch, tmp_path: Path) -> None:
    config = RemoteSandboxConfig(base_url="https://sandbox.example.com", api_key="secret", timeout_seconds=5)
    provider = RemoteThreadSandboxProvider(config)
    sandbox = provider.get(tmp_path / "threads" / "thread123")
    calls: list[tuple[str, str, dict[str, str]]] = []

    class _FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = json.dumps(payload).encode("utf-8")

        def read(self) -> bytes:
            return self.payload

        def __enter__(self) -> "_FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        body = req.data.decode("utf-8") if req.data else "{}"
        calls.append((req.method, req.full_url, dict(req.headers)))
        if req.full_url.endswith("/workspace"):
            return _FakeResponse({"root": "/remote/root", "workspace": "/remote/workspace", "uploads": "/remote/uploads", "outputs": "/remote/outputs"})
        if req.full_url.endswith("/write_text"):
            payload = json.loads(body)
            return _FakeResponse({"path": f"/remote/{payload['area']}/{payload['relative_path']}"})
        if req.full_url.endswith("/read_text"):
            return _FakeResponse({"content": "remote text"})
        if "/list_files" in req.full_url:
            return _FakeResponse({"files": ["a.txt", "b.txt"]})
        return _FakeResponse({"command": "echo hi", "exit_code": 0, "stdout": "hi", "stderr": "", "duration_ms": 1.0})

    monkeypatch.setattr(request, "urlopen", fake_urlopen)

    assert sandbox.workspace_paths()["workspace"] == "/remote/workspace"
    assert sandbox.write_text("demo.txt", "hello", area="outputs").as_posix() == "/remote/outputs/demo.txt"
    assert sandbox.read_text("demo.txt", area="outputs") == "remote text"
    assert sandbox.list_files("workspace") == ["a.txt", "b.txt"]
    assert sandbox.execute_command("echo hi").stdout == "hi"
    assert any("Authorization" in headers for _, _, headers in calls)


def test_workspace_stream_builder_compacts_thread_payload() -> None:
    payload = {
        "thread_id": "thread-1",
        "title": "Workspace",
        "status": "completed",
        "agent_name": "ResearchAgent",
        "latest_query": "hello",
        "workspace": {"workspace": "/tmp/workspace"},
        "messages": [{"role": "user", "content": "hello"}],
        "artifacts": [{"name": "summary.json", "kind": "run_summary"}],
        "executions": [{"execution_id": "exec1", "label": "mission", "status": "completed", "graph": {"summary": {"completed_nodes": 3, "node_count": 3, "runnable_nodes": []}}}],
        "events": [{"event": "execution_completed", "timestamp": "now"}],
    }
    stream = ThreadWorkspaceStreamBuilder().build(payload)

    assert stream["metrics"]["artifact_count"] == 1
    assert stream["executions"][0]["completed_nodes"] == 3
