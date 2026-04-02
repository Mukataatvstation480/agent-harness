"""Tests for harness-lab CI gate logic."""

from __future__ import annotations

from app.harness.ci_gate import _evaluate_preset


def test_ci_gate_evaluate_preset_passes_when_metrics_are_healthy() -> None:
    payload = {
        "best": {
            "candidate": "balanced-auto",
            "composite_score": 0.9,
            "pass_rate": 0.9,
            "avg_security_alignment": 1.0,
            "avg_value_index": 80.0,
        },
        "release_decision": {"decision": "go"},
        "competition": {"pareto_frontier": ["balanced-auto", "strict-daily"]},
    }
    baseline = {
        "presets": {
            "core": {
                "baseline_best_composite": 0.9,
                "min_best_composite": 0.8,
                "min_pass_rate": 0.7,
                "min_avg_security_alignment": 0.8,
                "min_avg_value_index": 70.0,
                "min_pareto_frontier_size": 1,
                "min_release_decision": "go",
            }
        }
    }
    global_cfg = {"max_abs_composite_drop": 0.08, "max_rel_composite_drop": 0.1}
    report = _evaluate_preset("core", payload, baseline, global_cfg)
    assert report["passed"] is True
    assert report["metrics"]["release_decision"] == "go"


def test_ci_gate_evaluate_preset_fails_on_regression() -> None:
    payload = {
        "best": {
            "candidate": "balanced-auto",
            "composite_score": 0.55,
            "pass_rate": 0.6,
            "avg_security_alignment": 0.5,
            "avg_value_index": 50.0,
        },
        "release_decision": {"decision": "block"},
        "competition": {"pareto_frontier": []},
    }
    baseline = {
        "presets": {
            "core": {
                "baseline_best_composite": 0.9,
                "min_best_composite": 0.8,
                "min_pass_rate": 0.7,
                "min_avg_security_alignment": 0.8,
                "min_avg_value_index": 70.0,
                "min_pareto_frontier_size": 1,
                "min_release_decision": "go",
            }
        }
    }
    global_cfg = {"max_abs_composite_drop": 0.08, "max_rel_composite_drop": 0.1}
    report = _evaluate_preset("core", payload, baseline, global_cfg)
    assert report["passed"] is False
    assert len(report["failed_checks"]) >= 1


def test_ci_gate_evaluate_preset_checks_category_coverage() -> None:
    payload = {
        "best": {
            "candidate": "balanced-auto",
            "composite_score": 0.9,
            "pass_rate": 0.9,
            "avg_security_alignment": 1.0,
            "avg_value_index": 80.0,
            "by_category": {
                "daily": {"avg_scenario_score": 0.7},
                "research": {"avg_scenario_score": 0.72},
            },
        },
        "release_decision": {"decision": "go"},
        "competition": {"pareto_frontier": ["balanced-auto"]},
    }
    baseline = {
        "presets": {
            "core": {
                "baseline_best_composite": 0.9,
                "min_best_composite": 0.8,
                "min_pass_rate": 0.7,
                "min_avg_security_alignment": 0.8,
                "min_avg_value_index": 70.0,
                "min_pareto_frontier_size": 1,
                "min_release_decision": "go",
            }
        }
    }
    global_cfg = {
        "max_abs_composite_drop": 0.08,
        "max_rel_composite_drop": 0.1,
        "min_category_coverage": 4,
        "min_worst_category_score": 0.62,
    }
    report = _evaluate_preset("core", payload, baseline, global_cfg)
    assert report["passed"] is False
    names = {item["name"] for item in report["failed_checks"]}
    assert "category_coverage" in names
