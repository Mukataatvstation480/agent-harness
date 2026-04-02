"""CI quality gate powered by harness research lab benchmarks."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.harness.engine import HarnessEngine

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE = ROOT / "data" / "harness_lab_ci_baseline.json"
DEFAULT_OUTPUT = ROOT / "reports" / "harness_lab_ci_result.json"


@dataclass
class GateCheck:
    """Single gate check result."""

    name: str
    passed: bool
    actual: Any
    expected: Any
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "actual": self.actual,
            "expected": self.expected,
            "details": self.details,
        }


def _decision_rank(name: str) -> int:
    key = str(name).strip().lower()
    if key == "go":
        return 2
    if key == "caution":
        return 1
    return 0


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_presets(value: str) -> list[str]:
    items = [item.strip().lower() for item in value.split(",") if item.strip()]
    if not items:
        return ["core"]
    return items


def _run_one_preset(
    engine: HarnessEngine,
    preset: str,
    repeats: int,
    seed: int,
) -> dict[str, Any]:
    return engine.run_research_lab(
        preset=preset,
        repeats=max(1, repeats),
        seed=seed,
        isolate_memory=True,
        fresh_memory_per_candidate=True,
    )


def _evaluate_preset(
    preset: str,
    payload: dict[str, Any],
    baseline: dict[str, Any],
    global_cfg: dict[str, Any],
) -> dict[str, Any]:
    preset_cfg = dict((baseline.get("presets", {}) or {}).get(preset, {}))
    best = dict(payload.get("best", {}))
    release = dict(payload.get("release_decision", {}))
    competition = dict(payload.get("competition", {}))

    decision = str(release.get("decision", "block")).lower()
    best_composite = float(best.get("composite_score", 0.0))
    best_pass_rate = float(best.get("pass_rate", 0.0))
    best_safety = float(best.get("avg_security_alignment", 0.0))
    best_value = float(best.get("avg_value_index", 0.0))
    frontier_size = len(list(competition.get("pareto_frontier", [])))
    by_category = dict(best.get("by_category", {})) if isinstance(best.get("by_category", {}), dict) else {}

    min_decision = str(preset_cfg.get("min_release_decision", global_cfg.get("min_release_decision", "caution")))
    min_composite = float(preset_cfg.get("min_best_composite", 0.75))
    min_pass_rate = float(preset_cfg.get("min_pass_rate", 0.67))
    min_safety = float(preset_cfg.get("min_avg_security_alignment", 0.75))
    min_value = float(preset_cfg.get("min_avg_value_index", 70.0))
    min_frontier = int(preset_cfg.get("min_pareto_frontier_size", 1))

    baseline_composite = float(preset_cfg.get("baseline_best_composite", 0.0))
    max_abs_drop = float(global_cfg.get("max_abs_composite_drop", 0.08))
    max_rel_drop = float(global_cfg.get("max_rel_composite_drop", 0.10))
    composite_drop = baseline_composite - best_composite
    composite_rel_drop = composite_drop / max(baseline_composite, 1e-9)

    checks = [
        GateCheck(
            name="release_decision",
            passed=_decision_rank(decision) >= _decision_rank(min_decision),
            actual=decision,
            expected=f">={min_decision}",
        ),
        GateCheck(
            name="best_composite_floor",
            passed=best_composite >= min_composite,
            actual=round(best_composite, 4),
            expected=f">={min_composite}",
        ),
        GateCheck(
            name="best_pass_rate_floor",
            passed=best_pass_rate >= min_pass_rate,
            actual=round(best_pass_rate, 4),
            expected=f">={min_pass_rate}",
        ),
        GateCheck(
            name="best_safety_floor",
            passed=best_safety >= min_safety,
            actual=round(best_safety, 4),
            expected=f">={min_safety}",
        ),
        GateCheck(
            name="best_value_floor",
            passed=best_value >= min_value,
            actual=round(best_value, 3),
            expected=f">={min_value}",
        ),
        GateCheck(
            name="pareto_frontier_size",
            passed=frontier_size >= min_frontier,
            actual=frontier_size,
            expected=f">={min_frontier}",
        ),
    ]

    if by_category:
        min_category_coverage = int(global_cfg.get("min_category_coverage", 4))
        min_worst_category_score = float(global_cfg.get("min_worst_category_score", 0.62))
        scores = [
            float(item.get("avg_scenario_score", 0.0))
            for item in by_category.values()
            if isinstance(item, dict)
        ]
        worst_category_score = min(scores) if scores else 0.0
        checks.append(
            GateCheck(
                name="category_coverage",
                passed=len(by_category) >= min_category_coverage,
                actual=len(by_category),
                expected=f">={min_category_coverage}",
            )
        )
        checks.append(
            GateCheck(
                name="worst_category_score_floor",
                passed=worst_category_score >= min_worst_category_score,
                actual=round(worst_category_score, 4),
                expected=f">={min_worst_category_score}",
            )
        )

    if baseline_composite > 0:
        checks.append(
            GateCheck(
                name="composite_regression_budget",
                passed=(composite_drop <= max_abs_drop) and (composite_rel_drop <= max_rel_drop),
                actual={
                    "current": round(best_composite, 4),
                    "baseline": round(baseline_composite, 4),
                    "abs_drop": round(composite_drop, 4),
                    "rel_drop": round(composite_rel_drop, 4),
                },
                expected={
                    "max_abs_drop": max_abs_drop,
                    "max_rel_drop": max_rel_drop,
                },
            )
        )

    failed = [item.to_dict() for item in checks if not item.passed]
    passed = len(failed) == 0
    return {
        "preset": preset,
        "passed": passed,
        "best_candidate": best.get("candidate", ""),
        "checks": [item.to_dict() for item in checks],
        "failed_checks": failed,
        "metrics": {
            "release_decision": decision,
            "best_composite": round(best_composite, 4),
            "best_pass_rate": round(best_pass_rate, 4),
            "best_safety": round(best_safety, 4),
            "best_value_index": round(best_value, 3),
            "pareto_frontier_size": frontier_size,
        },
    }


def _markdown_summary(results: list[dict[str, Any]], overall_passed: bool) -> str:
    lines = []
    lines.append("# Harness Lab CI Gate")
    lines.append("")
    lines.append(f"- Overall: {'PASS' if overall_passed else 'FAIL'}")
    lines.append("")
    for item in results:
        status = "PASS" if item.get("passed") else "FAIL"
        preset = item.get("preset")
        metrics = item.get("metrics", {})
        lines.append(f"## Preset `{preset}`: {status}")
        lines.append(
            "- Best: "
            f"{item.get('best_candidate', '-')}, "
            f"decision={metrics.get('release_decision')}, "
            f"composite={metrics.get('best_composite')}, "
            f"pass_rate={metrics.get('best_pass_rate')}"
        )
        failed = item.get("failed_checks", [])
        if failed:
            lines.append("- Failed checks:")
            for row in failed:
                lines.append(f"  - {row.get('name')}: actual={row.get('actual')} expected={row.get('expected')}")
        else:
            lines.append("- Failed checks: none")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run harness-lab CI quality gate.")
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE), help="Baseline config JSON path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON path")
    parser.add_argument("--presets", default="core,daily,research,strict,broad", help="Comma-separated preset list")
    parser.add_argument("--repeats", type=int, default=1, help="Repeat count per scenario")
    parser.add_argument("--seed", type=int, default=7, help="Seed for bootstrap CI")
    args = parser.parse_args(argv)

    baseline_path = Path(args.baseline)
    if not baseline_path.exists():
        print(f"[ci-gate] baseline file not found: {baseline_path}", file=sys.stderr)
        return 2

    baseline = _load_json(baseline_path)
    global_cfg = dict(baseline.get("global", {}))
    presets = _parse_presets(args.presets)
    engine = HarnessEngine()

    results: list[dict[str, Any]] = []
    lab_payloads: dict[str, Any] = {}
    for preset in presets:
        payload = _run_one_preset(engine=engine, preset=preset, repeats=args.repeats, seed=args.seed)
        lab_payloads[preset] = payload
        report = _evaluate_preset(
            preset=preset,
            payload=payload,
            baseline=baseline,
            global_cfg=global_cfg,
        )
        results.append(report)

    overall_passed = all(item.get("passed", False) for item in results)
    summary_md = _markdown_summary(results, overall_passed=overall_passed)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "overall_passed": overall_passed,
        "results": results,
        "lab_payloads": lab_payloads,
        "markdown_summary": summary_md,
    }
    output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    print(summary_md)
    if not overall_passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
