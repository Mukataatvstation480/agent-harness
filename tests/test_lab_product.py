"""Tests for productized harness-lab bundle outputs."""

from __future__ import annotations

from pathlib import Path

from app.harness.engine import HarnessEngine
from app.harness.lab_product import LabProductBuilder


def test_lab_product_bundle_builds_story_and_csv() -> None:
    engine = HarnessEngine()
    payload = engine.run_research_lab(
        preset="daily",
        repeats=1,
        scenario_ids=["daily-001"],
        isolate_memory=True,
        fresh_memory_per_candidate=True,
    )
    bundle = engine.build_lab_product_bundle(payload, tag="unit-test")
    assert bundle["run_tag"] == "unit-test"
    assert "summary" in bundle
    assert "applause_points" in bundle
    assert "markdown" in bundle and "# Harness Lab Product Story" in bundle["markdown"]
    assert "csv" in bundle and "candidate" in bundle["csv"]


def test_lab_product_write_bundle_and_history(tmp_path: Path) -> None:
    history_file = tmp_path / "history.json"
    builder = LabProductBuilder(history_file=history_file)
    fake = {
        "preset": "core",
        "scenario_count": 2,
        "candidate_count": 2,
        "release_decision": {"decision": "go", "reason": "all_quality_gates_passed"},
        "best": {
            "candidate": "balanced-auto",
            "composite_score": 0.9,
            "avg_value_index": 80.0,
        },
        "competition": {"pareto_frontier": ["balanced-auto"]},
        "leaderboard": [
            {
                "candidate": "balanced-auto",
                "runs": 2,
                "composite_score": 0.9,
                "avg_value_index": 80.0,
                "avg_scenario_score": 0.88,
                "avg_completion": 1.0,
                "avg_tool_success_rate": 1.0,
                "avg_security_alignment": 1.0,
                "efficiency_score": 0.95,
                "stability_score": 0.9,
                "pass_rate": 1.0,
                "pareto_frontier": True,
                "dominance_rank": 1,
            }
        ],
    }
    bundle = builder.build_bundle(fake, tag="fake")
    paths = builder.write_bundle(bundle, output_dir=tmp_path / "out")
    assert Path(paths.json_path).exists()
    assert Path(paths.markdown_path).exists()
    assert Path(paths.csv_path).exists()

    history = builder.list_history(limit=2)
    assert len(history) >= 1
    assert history[0]["run_tag"] == "fake"
