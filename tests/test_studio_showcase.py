"""Tests for flagship studio showcase pipeline and artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from app.harness.engine import HarnessEngine
from app.studio.flagship import FLAGSHIP_ONE_LINER, StudioShowcaseBuilder


def test_build_showcase_payload_shape() -> None:
    builder = StudioShowcaseBuilder(harness=HarnessEngine())
    payload = builder.build_showcase(
        query="Create a practical execution plan with risks and measurable checkpoints.",
        mode="balanced",
        lab_preset="daily",
        lab_repeats=1,
        scenario_ids=["daily-001"],
        include_marketplace=False,
        include_external=False,
        include_harness_tools=False,
        include_interop_catalog=False,
    )

    assert payload["identity"]["one_liner"] == FLAGSHIP_ONE_LINER
    assert payload["schema"] == "agent-harness-studio/v1"
    assert "story" in payload
    assert "proposal" in payload
    assert "agent_comparison" in payload
    assert "theme" in payload["story"]
    assert "release_need" in payload["story"]
    assert len(payload["story"].get("strategy_plan", [])) >= 3
    assert "harness" in payload and "plan" in payload["harness"]
    assert "final_answer_excerpt" in payload["harness"]
    assert "generation" in payload["harness"]
    assert "frontier" in payload
    assert payload["frontier"]["score"] >= 0.0
    assert payload["frontier"]["score"] <= 1.0
    assert "comparison" in payload
    assert len(payload["comparison"]["archetypes"]) >= 3
    assert "lab" in payload and "leaderboard" in payload["lab"]


def test_write_showcase_with_interop_bundle(tmp_path: Path) -> None:
    builder = StudioShowcaseBuilder(harness=HarnessEngine())
    payload = builder.build_showcase(
        query="Benchmark strategy options and produce a governance-ready recommendation.",
        mode="balanced",
        lab_preset="daily",
        lab_repeats=1,
        scenario_ids=["daily-001"],
        include_marketplace=False,
        include_external=False,
        include_harness_tools=False,
        include_interop_catalog=True,
    )
    paths = builder.write_showcase(
        payload=payload,
        output_dir=str(tmp_path),
        tag="unit",
        export_interop=True,
    )

    json_path = Path(paths["json"])
    html_path = Path(paths["html"])
    assert json_path.exists()
    assert html_path.exists()

    interop = paths.get("interop", {})
    assert isinstance(interop, dict)
    assert Path(str(interop.get("index", ""))).exists()

    written = json.loads(json_path.read_text(encoding="utf-8"))
    assert "catalog" not in written.get("interop", {})
    html_content = html_path.read_text(encoding="utf-8")
    assert "Agent Harness Studio" in html_content
    assert "What Is Being Launched" in html_content
    assert "Three-Phase Rollout" in html_content
    assert "Agent Comparison" in html_content
    assert "Appendix" in html_content
