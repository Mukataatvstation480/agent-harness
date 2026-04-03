"""Unified benchmark adapters and ablation runner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.benchmark.evaluate import run_benchmark


@dataclass(frozen=True)
class BenchmarkAdapterSpec:
    """One benchmark adapter that emits standardized result payloads."""

    name: str
    family: str
    description: str
    execution_mode: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "family": self.family,
            "description": self.description,
            "execution_mode": self.execution_mode,
        }


class BenchmarkAdapterRunner:
    """Run internal benchmark adapters and ablation studies under one schema."""

    SCHEMA = "agent-harness-benchmark-suite/v1"

    def list_adapters(self) -> list[dict[str, str]]:
        return [item.to_dict() for item in self._defaults()]

    def run_suite(
        self,
        engine: Any,
        adapters: list[str] | None = None,
        repeats: int = 1,
    ) -> dict[str, Any]:
        active = self._resolve_adapters(adapters)
        results: list[dict[str, Any]] = []
        for spec in active:
            if spec.name == "routing_internal":
                results.append(self._run_routing_internal())
            elif spec.name == "lab_daily":
                results.append(
                    self._run_lab_adapter(
                        engine=engine,
                        preset="daily",
                        scenario_ids=["daily-001", "enterprise-001"],
                        repeats=repeats,
                        spec=spec,
                    )
                )
            elif spec.name == "lab_research":
                results.append(
                    self._run_lab_adapter(
                        engine=engine,
                        preset="research",
                        scenario_ids=["research-001", "enterprise-001"],
                        repeats=repeats,
                        spec=spec,
                    )
                )
        return {
            "schema": self.SCHEMA,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "adapters": results,
            "failure_summary": self._suite_failure_summary(results),
        }

    def run_ablation(
        self,
        engine: Any,
        repeats: int = 1,
        scenario_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        candidates = [
            {"name": "baseline-balanced", "mode": "balanced"},
            {
                "name": "no-discovery",
                "mode": "balanced",
                "constraints_overrides": {"enable_dynamic_discovery": False},
            },
            {
                "name": "strict-contained",
                "mode": "safety_critical",
                "recipe": "risk-radar",
                "constraints_overrides": {
                    "security_strictness": "strict",
                    "allow_network_actions": False,
                    "allow_browser_actions": False,
                },
            },
            {"name": "research-rig", "mode": "deep", "recipe": "research-rig"},
            {"name": "enterprise-ops", "mode": "safety_critical", "recipe": "enterprise-ops"},
        ]
        payload = engine.run_research_lab(
            preset="broad",
            candidates=candidates,
            scenario_ids=scenario_ids or ["daily-001", "research-001", "enterprise-001", "safety-001"],
            repeats=max(1, repeats),
            include_runs=False,
            isolate_memory=True,
            fresh_memory_per_candidate=True,
        )
        leaderboard = payload.get("leaderboard", [])
        baseline = next((row for row in leaderboard if row.get("candidate") == "baseline-balanced"), leaderboard[0] if leaderboard else {})
        deltas = self._ablation_deltas(leaderboard=leaderboard, baseline=baseline)
        failures = self._lab_failure_clusters(payload.get("records", []))
        return {
            "schema": "agent-harness-benchmark-ablation/v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "baseline": baseline,
            "leaderboard": leaderboard,
            "deltas": deltas,
            "failure_clusters": failures,
            "release_decision": payload.get("release_decision", {}),
            "scenario_ids": payload.get("scenario_ids", scenario_ids or []),
        }

    @staticmethod
    def _run_routing_internal() -> dict[str, Any]:
        payload = run_benchmark()
        details = payload.get("details", [])
        failures: dict[str, int] = {
            "complementary_miss": 0,
            "greedy_outperforms": 0,
        }
        for row in details:
            scores = row.get("scores", {})
            comp = float(scores.get("complementary", 0.0))
            greedy = float(scores.get("greedy", 0.0))
            if comp < 1.0:
                failures["complementary_miss"] += 1
            if greedy > comp:
                failures["greedy_outperforms"] += 1
        return {
            "name": "routing_internal",
            "family": "internal-routing",
            "description": "Greedy vs random vs complementary skill routing.",
            "metrics": {
                "count": int(payload.get("count", 0)),
                "greedy": float(payload.get("greedy", 0.0)),
                "random": float(payload.get("random", 0.0)),
                "complementary": float(payload.get("complementary", 0.0)),
            },
            "comparison": {
                "complementary_vs_greedy": round(float(payload.get("complementary", 0.0)) - float(payload.get("greedy", 0.0)), 4),
                "complementary_vs_random": round(float(payload.get("complementary", 0.0)) - float(payload.get("random", 0.0)), 4),
            },
            "failure_clusters": [{"name": key, "count": value} for key, value in failures.items()],
        }

    @staticmethod
    def _run_lab_adapter(
        engine: Any,
        preset: str,
        scenario_ids: list[str],
        repeats: int,
        spec: BenchmarkAdapterSpec,
    ) -> dict[str, Any]:
        payload = engine.run_research_lab(
            preset=preset,
            repeats=max(1, repeats),
            scenario_ids=scenario_ids,
            include_runs=False,
            isolate_memory=True,
            fresh_memory_per_candidate=True,
        )
        failures = BenchmarkAdapterRunner._lab_failure_clusters(payload.get("records", []))
        return {
            "name": spec.name,
            "family": spec.family,
            "description": spec.description,
            "metrics": {
                "best_candidate": payload.get("best", {}).get("candidate", ""),
                "best_composite": float(payload.get("best", {}).get("composite_score", 0.0)),
                "release_decision": payload.get("release_decision", {}).get("decision", "block"),
                "release_reason": payload.get("release_decision", {}).get("reason", ""),
            },
            "leaderboard": payload.get("leaderboard", []),
            "failure_clusters": failures,
        }

    @staticmethod
    def _lab_failure_clusters(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counters: dict[str, dict[str, Any]] = {}
        def bump(name: str, record: dict[str, Any]) -> None:
            row = counters.setdefault(name, {"name": name, "count": 0, "examples": []})
            row["count"] += 1
            if len(row["examples"]) < 3:
                row["examples"].append(
                    {
                        "candidate": record.get("candidate", ""),
                        "scenario_id": record.get("scenario_id", ""),
                    }
                )
        for record in records:
            if float(record.get("completion", 0.0)) < 0.75:
                bump("low_completion", record)
            if float(record.get("expected_tool_coverage", 0.0)) < 0.5:
                bump("tool_coverage_gap", record)
            if float(record.get("security_alignment", 0.0)) < 0.95:
                bump("security_alignment_gap", record)
            if float(record.get("value_index", 0.0)) < 70.0:
                bump("low_value_index", record)
        return sorted(counters.values(), key=lambda item: int(item.get("count", 0)), reverse=True)

    @staticmethod
    def _suite_failure_summary(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in results:
            for cluster in item.get("failure_clusters", []):
                rows.append(
                    {
                        "adapter": item.get("name", ""),
                        "cluster": cluster.get("name", ""),
                        "count": int(cluster.get("count", 0)),
                    }
                )
        rows.sort(key=lambda item: item["count"], reverse=True)
        return rows[:10]

    @staticmethod
    def _ablation_deltas(leaderboard: list[dict[str, Any]], baseline: dict[str, Any]) -> list[dict[str, Any]]:
        baseline_score = float(baseline.get("composite_score", 0.0))
        baseline_value = float(baseline.get("avg_value_index", 0.0))
        baseline_pass = float(baseline.get("pass_rate", 0.0))
        rows: list[dict[str, Any]] = []
        for item in leaderboard:
            rows.append(
                {
                    "candidate": item.get("candidate", ""),
                    "delta_composite": round(float(item.get("composite_score", 0.0)) - baseline_score, 4),
                    "delta_value_index": round(float(item.get("avg_value_index", 0.0)) - baseline_value, 4),
                    "delta_pass_rate": round(float(item.get("pass_rate", 0.0)) - baseline_pass, 4),
                }
            )
        return rows

    def _resolve_adapters(self, adapters: list[str] | None = None) -> list[BenchmarkAdapterSpec]:
        all_specs = self._defaults()
        if not adapters:
            return all_specs
        wanted = {item.strip() for item in adapters if item.strip()}
        return [item for item in all_specs if item.name in wanted]

    @staticmethod
    def _defaults() -> list[BenchmarkAdapterSpec]:
        return [
            BenchmarkAdapterSpec(
                name="routing_internal",
                family="internal-routing",
                description="Legacy routing benchmark for skill selection quality.",
                execution_mode="native",
            ),
            BenchmarkAdapterSpec(
                name="lab_daily",
                family="task-pack-daily",
                description="Daily and enterprise harness-lab evaluation under mission-pack runtime.",
                execution_mode="harness_lab",
            ),
            BenchmarkAdapterSpec(
                name="lab_research",
                family="task-pack-research",
                description="Research and promotion-oriented harness-lab evaluation.",
                execution_mode="harness_lab",
            ),
        ]
