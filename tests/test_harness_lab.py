"""Tests for research lab and newly added harness tools."""

from __future__ import annotations

from app.harness.engine import HarnessEngine
from app.harness.models import HarnessConstraints, ToolCall, ToolType
from app.harness.tools import ToolRegistry


def test_research_lab_lists_scenarios_and_presets() -> None:
    engine = HarnessEngine()
    scenarios = engine.list_research_scenarios()
    presets = engine.list_research_presets()

    assert len(scenarios) >= 6
    assert any(item.get("category") == "daily" for item in scenarios)
    assert any(item.get("category") == "research" for item in scenarios)
    assert any(item.get("category") == "safety" for item in scenarios)
    assert any(item.get("category") == "creative" for item in scenarios)
    assert any(item.get("category") == "enterprise" for item in scenarios)
    assert any(item.get("name") == "core" for item in presets)
    assert any(item.get("name") == "broad" for item in presets)


def test_research_lab_run_returns_ranked_leaderboard() -> None:
    engine = HarnessEngine()
    payload = engine.run_research_lab(
        preset="daily",
        repeats=1,
        scenario_ids=["daily-001", "daily-002"],
        constraints=HarnessConstraints(max_steps=4, max_tool_calls=4),
    )

    assert payload["scenario_count"] == 2
    assert payload["candidate_count"] >= 2
    assert len(payload["leaderboard"]) >= 2
    assert "best" in payload
    assert "composite_score" in payload["leaderboard"][0]
    assert "ci95_value_index" in payload["leaderboard"][0]
    assert "competition" in payload
    assert "pareto_frontier" in payload["competition"]
    assert "release_decision" in payload
    assert payload["release_decision"]["decision"] in {"go", "caution", "block"}
    repro = payload.get("reproducibility", {})
    assert repro.get("isolate_memory") is True
    assert repro.get("fresh_memory_per_candidate") is True


def test_tool_registry_new_tools_output_shape() -> None:
    tools = ToolRegistry()

    portfolio = tools.call(
        ToolCall(
            name="api_skill_portfolio_optimizer",
            tool_type=ToolType.API,
            args={"query": "daily planning and vendor comparison", "limit": 3},
        )
    )
    assert portfolio.success is True
    assert "portfolio" in portfolio.output
    assert "portfolio_summary" in portfolio.output

    design = tools.call(
        ToolCall(
            name="code_experiment_design",
            tool_type=ToolType.CODE,
            args={"query": "ablation benchmark for multi-agent routing", "max_experiments": 4},
        )
    )
    assert design.success is True
    assert "experiment_matrix" in design.output
    assert len(design.output["experiment_matrix"]) == 4
