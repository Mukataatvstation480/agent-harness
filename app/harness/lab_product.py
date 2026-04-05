"""Productized output bundle builder for harness-lab results."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_FILE = Path(__file__).resolve().parents[2] / "data" / "harness_lab_history.json"


@dataclass
class LabBundlePaths:
    """Paths for generated product bundle artifacts."""

    json_path: str
    markdown_path: str
    csv_path: str
    history_path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "json": self.json_path,
            "markdown": self.markdown_path,
            "csv": self.csv_path,
            "history": self.history_path,
        }


class LabProductBuilder:
    """Build customer-facing artifacts from research-lab payload."""

    def __init__(self, history_file: Path | None = None) -> None:
        self._history_file = history_file or HISTORY_FILE
        self._ensure_history()

    def build_bundle(
        self,
        lab_payload: dict[str, Any],
        tag: str = "",
    ) -> dict[str, Any]:
        """Build bundle payload without writing files."""

        run_tag = tag.strip() or datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S")
        history = self._load_history()
        trend = self._trend_summary(lab_payload, history)
        streak = self._champion_streak(lab_payload, history)
        summary = self._summary_card(lab_payload, trend=trend, streak=streak)
        applause_points = self._applause_points(lab_payload, trend=trend, streak=streak)
        markdown = self._to_markdown(run_tag, summary, applause_points, lab_payload, trend, streak)
        csv_data = self._to_csv(lab_payload)

        return {
            "run_tag": run_tag,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "applause_points": applause_points,
            "trend": trend,
            "champion_streak": streak,
            "release_decision": lab_payload.get("release_decision", {}),
            "best": lab_payload.get("best", {}),
            "competition": lab_payload.get("competition", {}),
            "reproducibility": lab_payload.get("reproducibility", {}),
            "leaderboard": lab_payload.get("leaderboard", []),
            "markdown": markdown,
            "csv": csv_data,
        }

    def write_bundle(
        self,
        bundle: dict[str, Any],
        output_dir: Path,
    ) -> LabBundlePaths:
        """Write bundle to JSON/Markdown/CSV files and return paths."""

        output_dir.mkdir(parents=True, exist_ok=True)
        run_tag = str(bundle.get("run_tag", "run"))
        json_path = output_dir / f"harness_lab_bundle_{run_tag}.json"
        markdown_path = output_dir / f"harness_lab_story_{run_tag}.md"
        csv_path = output_dir / f"harness_lab_leaderboard_{run_tag}.csv"

        json_payload = dict(bundle)
        markdown = str(json_payload.pop("markdown", ""))
        csv_data = str(json_payload.pop("csv", ""))

        json_path.write_text(json.dumps(json_payload, indent=2, default=str), encoding="utf-8")
        markdown_path.write_text(markdown, encoding="utf-8")
        csv_path.write_text(csv_data, encoding="utf-8")

        self._append_history(
            {
                "run_tag": run_tag,
                "generated_at": bundle.get("generated_at", ""),
                "preset": bundle.get("summary", {}).get("preset", ""),
                "best_candidate": bundle.get("summary", {}).get("best_candidate", ""),
                "best_composite_score": bundle.get("summary", {}).get("best_composite_score", 0.0),
                "best_value_index": bundle.get("summary", {}).get("best_value_index", 0.0),
                "release_decision": bundle.get("summary", {}).get("release_decision", ""),
                "pareto_frontier_size": bundle.get("summary", {}).get("pareto_frontier_size", 0),
            }
        )

        return LabBundlePaths(
            json_path=str(json_path),
            markdown_path=str(markdown_path),
            csv_path=str(csv_path),
            history_path=str(self._history_file),
        )

    def list_history(self, limit: int = 12) -> list[dict[str, Any]]:
        """Return latest productized lab runs."""

        history = self._load_history()
        runs = history.get("runs", [])
        if not isinstance(runs, list):
            return []
        return list(reversed(runs[-max(1, limit) :]))

    def _ensure_history(self) -> None:
        self._history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self._history_file.exists():
            self._history_file.write_text(json.dumps({"runs": []}, indent=2), encoding="utf-8")

    def _load_history(self) -> dict[str, Any]:
        self._ensure_history()
        return json.loads(self._history_file.read_text(encoding="utf-8"))

    def _append_history(self, row: dict[str, Any]) -> None:
        payload = self._load_history()
        runs = payload.setdefault("runs", [])
        if not isinstance(runs, list):
            runs = []
            payload["runs"] = runs
        runs.append(row)
        self._history_file.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    @staticmethod
    def _summary_card(
        lab_payload: dict[str, Any],
        trend: dict[str, Any],
        streak: dict[str, Any],
    ) -> dict[str, Any]:
        best = dict(lab_payload.get("best", {}))
        release = dict(lab_payload.get("release_decision", {}))
        frontier = list((lab_payload.get("competition", {}) or {}).get("pareto_frontier", []))
        return {
            "preset": str(lab_payload.get("preset", "")),
            "scenario_count": int(lab_payload.get("scenario_count", 0)),
            "candidate_count": int(lab_payload.get("candidate_count", 0)),
            "best_candidate": str(best.get("candidate", "")),
            "best_composite_score": round(float(best.get("composite_score", 0.0)), 4),
            "best_value_index": round(float(best.get("avg_value_index", 0.0)), 3),
            "release_decision": str(release.get("decision", "block")),
            "release_reason": str(release.get("reason", "")),
            "pareto_frontier_size": len(frontier),
            "composite_delta_vs_prev": round(float(trend.get("composite_delta", 0.0)), 4),
            "champion_streak": int(streak.get("streak", 0)),
        }

    @staticmethod
    def _trend_summary(lab_payload: dict[str, Any], history: dict[str, Any]) -> dict[str, Any]:
        runs = history.get("runs", [])
        previous = runs[-1] if isinstance(runs, list) and runs else {}
        best = dict(lab_payload.get("best", {}))
        current_composite = float(best.get("composite_score", 0.0))
        current_value = float(best.get("avg_value_index", 0.0))

        prev_composite = float(previous.get("best_composite_score", 0.0)) if isinstance(previous, dict) else 0.0
        prev_value = float(previous.get("best_value_index", 0.0)) if isinstance(previous, dict) else 0.0

        return {
            "has_previous": bool(previous),
            "previous_run_tag": str(previous.get("run_tag", "")) if isinstance(previous, dict) else "",
            "composite_delta": current_composite - prev_composite,
            "value_index_delta": current_value - prev_value,
        }

    @staticmethod
    def _champion_streak(lab_payload: dict[str, Any], history: dict[str, Any]) -> dict[str, Any]:
        runs = history.get("runs", [])
        champion = str((lab_payload.get("best", {}) or {}).get("candidate", ""))
        if not champion:
            return {"candidate": "", "streak": 0}
        streak = 1
        if isinstance(runs, list):
            for item in reversed(runs):
                if not isinstance(item, dict):
                    continue
                if str(item.get("best_candidate", "")) == champion:
                    streak += 1
                else:
                    break
        return {"candidate": champion, "streak": streak}

    @staticmethod
    def _applause_points(
        lab_payload: dict[str, Any],
        trend: dict[str, Any],
        streak: dict[str, Any],
    ) -> list[str]:
        best = dict(lab_payload.get("best", {}))
        release = dict(lab_payload.get("release_decision", {}))
        frontier = list((lab_payload.get("competition", {}) or {}).get("pareto_frontier", []))
        points = [
            f"Release gate decision is `{release.get('decision', 'block')}` with reason `{release.get('reason', '')}`.",
            f"Best candidate `{best.get('candidate', '-')}` reached composite score {round(float(best.get('composite_score', 0.0)), 4)}.",
            f"Pareto frontier includes {len(frontier)} candidate(s): {', '.join(frontier) if frontier else 'none'}.",
        ]
        if trend.get("has_previous"):
            points.append(
                "Trend vs previous run: "
                f"composite {round(float(trend.get('composite_delta', 0.0)), 4):+}, "
                f"value_index {round(float(trend.get('value_index_delta', 0.0)), 3):+}."
            )
        else:
            points.append("No previous run found; this run establishes the initial regression history.")

        if int(streak.get("streak", 0)) >= 3:
            points.append(
                f"Champion streak: `{streak.get('candidate', '')}` has led for {streak.get('streak')} consecutive runs."
            )
        return points

    @staticmethod
    def _to_markdown(
        run_tag: str,
        summary: dict[str, Any],
        applause_points: list[str],
        lab_payload: dict[str, Any],
        trend: dict[str, Any],
        streak: dict[str, Any],
    ) -> str:
        lines: list[str] = []
        lines.append("# Harness Lab Product Story")
        lines.append("")
        lines.append(f"- Run Tag: `{run_tag}`")
        lines.append(f"- Preset: `{summary.get('preset', '')}`")
        lines.append(f"- Release Decision: `{summary.get('release_decision', '')}`")
        lines.append(f"- Best Candidate: `{summary.get('best_candidate', '')}`")
        lines.append(f"- Composite Score: `{summary.get('best_composite_score', 0.0)}`")
        lines.append(f"- Value Index: `{summary.get('best_value_index', 0.0)}`")
        lines.append("")
        lines.append("## Why This Is Valuable")
        for item in applause_points:
            lines.append(f"- {item}")

        lines.append("")
        lines.append("## Competitive Snapshot")
        lines.append("| Candidate | Composite | Value | Pass Rate | Safety | Pareto |")
        lines.append("|-----------|-----------|-------|-----------|--------|--------|")
        for row in lab_payload.get("leaderboard", []):
            if not isinstance(row, dict):
                continue
            lines.append(
                "| "
                f"{row.get('candidate', '')} | "
                f"{row.get('composite_score', 0.0)} | "
                f"{row.get('avg_value_index', 0.0)} | "
                f"{row.get('pass_rate', 0.0)} | "
                f"{row.get('avg_security_alignment', 0.0)} | "
                f"{'yes' if row.get('pareto_frontier') else 'no'} |"
            )

        lines.append("")
        lines.append("## Trend")
        if trend.get("has_previous"):
            lines.append(f"- Previous Run: `{trend.get('previous_run_tag', '')}`")
            lines.append(f"- Composite Delta: `{round(float(trend.get('composite_delta', 0.0)), 4):+}`")
            lines.append(f"- Value Index Delta: `{round(float(trend.get('value_index_delta', 0.0)), 3):+}`")
        else:
            lines.append("- Previous run not found.")
        lines.append(f"- Champion Streak: `{streak.get('candidate', '')}` x `{streak.get('streak', 0)}`")
        lines.append("")
        return "\n".join(lines).strip() + "\n"

    @staticmethod
    def _to_csv(lab_payload: dict[str, Any]) -> str:
        headers = [
            "candidate",
            "runs",
            "composite_score",
            "avg_value_index",
            "avg_scenario_score",
            "avg_completion",
            "avg_tool_success_rate",
            "avg_security_alignment",
            "efficiency_score",
            "stability_score",
            "pass_rate",
            "pareto_frontier",
            "dominance_rank",
        ]
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        for row in lab_payload.get("leaderboard", []):
            if not isinstance(row, dict):
                continue
            writer.writerow({key: row.get(key, "") for key in headers})
        return stream.getvalue()
