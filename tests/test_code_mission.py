"""Tests for engineering-oriented code mission packs."""

from __future__ import annotations

from pathlib import Path

from app.harness.code_mission import CodeMissionPackBuilder
from app.harness.engine import HarnessEngine
from app.harness.models import HarnessConstraints, HarnessRun


def test_build_code_mission_pack_contains_patch_and_validation() -> None:
    engine = HarnessEngine()
    run = engine.run(
        query="Design an implementation roadmap with migration risks and validation gates.",
        constraints=HarnessConstraints(max_steps=3, max_tool_calls=3),
    )
    payload = engine.build_code_mission_pack(run, workspace=".")

    assert payload["schema"] == "agent-harness-code-mission/v1"
    assert payload["patch"]["status"] in {"captured", "draft", "empty"}
    assert "patch_stub" in payload["patch"]
    assert "tests" in payload and payload["tests"]["commands"]
    assert "execution_trace" in payload and len(payload["execution_trace"]) >= 1
    assert payload["validation_report"]["status"] in {"ready", "needs_review"}
    assert payload["task_graph"]["schema"] == "agent-harness-executable-task-graph/v1"
    assert payload["workspace_snapshot"]["root"]


def test_code_mission_pack_executes_validation_commands(tmp_path: Path) -> None:
    source = tmp_path / "router.py"
    source.write_text(
        "def normalize(value: str) -> str:\n"
        "    return value.strip().lower()\n",
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_router.py").write_text(
        "import sys\n"
        "from pathlib import Path\n\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n"
        "from router import normalize\n\n"
        "def test_normalize() -> None:\n"
        "    assert normalize('  HELLO ') == 'hello'\n",
        encoding="utf-8",
    )
    run = HarnessRun(
        query="Improve router validation path",
        plan=["Inspect router", "Run targeted validation"],
        steps=[],
        final_answer="ready",
        completed=True,
        eval_metrics={},
    )
    payload = CodeMissionPackBuilder().build(
        query=run.query,
        run=run,
        run_summary={"steps": [], "evidence": {}},
        workspace=tmp_path,
        execute_validation=True,
        validation_timeout_seconds=60,
        max_validation_commands=1,
    )

    assert payload["tests"]["targeted_files"] == ["tests/test_router.py"]
    assert payload["validation_report"]["execution_summary"]["executed"] == 1
    assert payload["validation_report"]["executions"][0]["status"] == "passed"
    assert payload["task_graph"]["summary"]["completed_nodes"] >= 3
