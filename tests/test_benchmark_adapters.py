"""Tests for unified benchmark adapters and ablation outputs."""

from __future__ import annotations

from app.benchmark.adapters import BenchmarkAdapterRunner
from app.harness.engine import HarnessEngine


def test_benchmark_adapter_registry_lists_defaults() -> None:
    runner = BenchmarkAdapterRunner()
    adapters = runner.list_adapters()
    names = {item["name"] for item in adapters}
    assert "routing_internal" in names
    assert "lab_daily" in names
    assert "lab_research" in names


def test_benchmark_suite_runs_selected_adapters() -> None:
    runner = BenchmarkAdapterRunner()
    payload = runner.run_suite(engine=HarnessEngine(), adapters=["routing_internal"], repeats=1)
    assert payload["schema"] == "agent-harness-benchmark-suite/v1"
    assert len(payload["adapters"]) == 1
    assert payload["adapters"][0]["name"] == "routing_internal"
    assert "failure_summary" in payload


def test_benchmark_ablation_returns_deltas_and_failures() -> None:
    runner = BenchmarkAdapterRunner()
    payload = runner.run_ablation(
        engine=HarnessEngine(),
        repeats=1,
        scenario_ids=["daily-001", "research-001"],
    )
    assert payload["schema"] == "agent-harness-benchmark-ablation/v1"
    assert payload["baseline"]["candidate"] == "baseline-balanced"
    assert len(payload["deltas"]) >= 1
    assert "failure_clusters" in payload
