"""Tests for engineering-oriented code mission packs."""

from __future__ import annotations

from app.harness.engine import HarnessEngine
from app.harness.models import HarnessConstraints


def test_build_code_mission_pack_contains_patch_and_validation() -> None:
    engine = HarnessEngine()
    run = engine.run(
        query="Design an implementation roadmap with migration risks and validation gates.",
        constraints=HarnessConstraints(max_steps=3, max_tool_calls=3),
    )
    payload = engine.build_code_mission_pack(run, workspace=".")

    assert payload["schema"] == "agent-harness-code-mission/v1"
    assert payload["patch"]["status"] == "draft"
    assert "patch_stub" in payload["patch"]
    assert "tests" in payload and payload["tests"]["commands"]
    assert "execution_trace" in payload and len(payload["execution_trace"]) >= 1
    assert payload["validation_report"]["status"] in {"ready", "needs_review"}
