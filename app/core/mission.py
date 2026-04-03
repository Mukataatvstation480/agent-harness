"""Shared mission-pack protocol for runtime and showcase outputs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


def _clean_text(value: object) -> str:
    text = str(value or "").strip()
    return re.sub(r"\s+", " ", text)


def _dedupe(items: list[object], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for item in items:
        text = _clean_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        rows.append(text)
        if len(rows) >= limit:
            break
    return rows


@dataclass(frozen=True)
class MissionDeliverableBlueprint:
    """One user-visible deliverable emitted by a mission pack."""

    title: str
    description: str
    audience: str

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "description": self.description,
            "audience": self.audience,
        }


@dataclass(frozen=True)
class BenchmarkTargetBlueprint:
    """Benchmark family that is relevant to a mission type."""

    name: str
    fit: str
    strength: str
    gap: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "fit": self.fit,
            "strength": self.strength,
            "gap": self.gap,
        }


@dataclass(frozen=True)
class MissionProfile:
    """Generalized product profile for one class of user task."""

    name: str
    title: str
    summary: str
    primary_deliverable: str
    target_users: list[str]
    output_views: list[str]
    review_questions: list[str]
    deliverables: list[MissionDeliverableBlueprint] = field(default_factory=list)
    benchmark_targets: list[BenchmarkTargetBlueprint] = field(default_factory=list)
    keyword_patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "summary": self.summary,
            "primary_deliverable": self.primary_deliverable,
            "target_users": list(self.target_users),
            "output_views": list(self.output_views),
            "review_questions": list(self.review_questions),
            "deliverables": [item.to_dict() for item in self.deliverables],
            "benchmark_targets": [item.to_dict() for item in self.benchmark_targets],
            "keyword_patterns": list(self.keyword_patterns),
        }


class MissionRegistry:
    """Infer the best mission-pack profile for a query."""

    def __init__(self) -> None:
        self._profiles = self._defaults()

    def infer(self, query: str) -> MissionProfile:
        text = query.lower().strip()
        best = self._profiles[0]
        best_score = -1
        for profile in self._profiles:
            score = sum(1 for pattern in profile.keyword_patterns if re.search(pattern, text))
            if score > best_score:
                best = profile
                best_score = score
        return best

    def list_cards(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self._profiles]

    def build_runtime_pack(
        self,
        query: str,
        run: Any,
        run_summary: dict[str, Any],
        profile: MissionProfile | None = None,
    ) -> dict[str, Any]:
        profile = profile or self.infer(query)
        metadata = run.metadata if hasattr(run, "metadata") and isinstance(run.metadata, dict) else {}
        evidence = run_summary.get("evidence", {}) if isinstance(run_summary, dict) else {}
        value_card = run_summary.get("value_card", {}) if isinstance(run_summary, dict) else {}
        recipe = run_summary.get("recipe", {}) if isinstance(run_summary, dict) else {}
        live = run_summary.get("live_agent", {}) if isinstance(run_summary, dict) else {}
        security = run_summary.get("security", {}) if isinstance(run_summary, dict) else {}
        selected_agent = _clean_text(metadata.get("selected_agent", ""))
        selected_skills = metadata.get("selected_skills", []) if isinstance(metadata.get("selected_skills", []), list) else []
        execution_plan = _dedupe(run_summary.get("plan", []), limit=10)
        deliverables = self._runtime_deliverables(
            profile=profile,
            final_answer=_clean_text(getattr(run, "final_answer", "")),
            execution_plan=execution_plan,
            evidence=evidence,
            live=live,
        )
        review_questions = _dedupe(
            list(profile.review_questions)
            + [
                f"What evidence would invalidate the current {profile.title.lower()} recommendation?",
                "Which deliverable is ready for stakeholder review today?",
                "Which benchmark family is the right proof target for this mission?",
            ],
            limit=6,
        )
        benchmark_targets = self._runtime_benchmark_targets(
            profile=profile,
            completed=bool(getattr(run, "completed", False)),
            live=live,
            selected_skills=selected_skills,
        )
        runtime_state = {
            "completed": bool(getattr(run, "completed", False)),
            "selected_agent": selected_agent,
            "selected_skills": selected_skills[:8],
            "recipe": {
                "name": _clean_text(recipe.get("name", "")),
                "executed_steps": int(recipe.get("executed_steps", 0)),
                "total_steps": int(recipe.get("total_steps", 0)),
            },
            "value_index": float(value_card.get("value_index", 0.0)),
            "band": _clean_text(value_card.get("band", "")),
            "mode": _clean_text(metadata.get("mode", "")),
            "risk_level": _clean_text(metadata.get("risk_level", "")),
        }
        execution_tracks = self._runtime_execution_tracks(
            execution_plan=execution_plan,
            security=security,
            evidence=evidence,
        )
        honest_boundary = self._runtime_boundary(profile)
        return {
            "name": profile.name,
            "title": profile.title,
            "summary": profile.summary,
            "primary_deliverable": profile.primary_deliverable,
            "query": query,
            "target_users": list(profile.target_users),
            "output_views": list(profile.output_views),
            "deliverables": deliverables,
            "review_questions": review_questions,
            "execution_tracks": execution_tracks,
            "benchmark_targets": benchmark_targets,
            "evidence_snapshot": {
                "record_count": int(evidence.get("record_count", 0)),
                "citation_count": int(evidence.get("citation_count", 0)),
                "citations": list(evidence.get("citations", []))[:6],
            },
            "runtime_state": runtime_state,
            "decision": {
                "status": "ready" if bool(getattr(run, "completed", False)) else "blocked",
                "reason": "runtime_completed" if bool(getattr(run, "completed", False)) else "runtime_incomplete",
                "selected_candidate": selected_agent,
                "value_index": float(value_card.get("value_index", 0.0)),
            },
            "honest_boundary": honest_boundary,
        }

    def build_release_pack(
        self,
        query: str,
        run: Any,
        run_summary: dict[str, Any],
        scenario: dict[str, Any],
        story: dict[str, Any],
        proposal: dict[str, Any],
        lab_payload: dict[str, Any],
        agent_comparison: dict[str, Any],
        profile: MissionProfile | None = None,
    ) -> dict[str, Any]:
        base = self.build_runtime_pack(query=query, run=run, run_summary=run_summary, profile=profile)
        evidence = run_summary.get("evidence", {}) if isinstance(run_summary, dict) else {}
        release = lab_payload.get("release_decision", {}) if isinstance(lab_payload, dict) else {}
        target_users = _dedupe(
            list(proposal.get("target_users", []))
            + list(base.get("target_users", []))
            + [story.get("audience_takeaway", "")]
        )
        review_questions = _dedupe(
            list(base.get("review_questions", []))
            + [
                release.get("reason", ""),
                f"Does the evidence packet support expansion beyond {scenario.get('name', 'this mission')}?",
                f"Is {agent_comparison.get('winner', 'the selected agent')} still the right owner if constraints tighten?",
            ],
            limit=6,
        )
        execution_plan = _dedupe(proposal.get("execution_plan", []) or run_summary.get("plan", []), limit=10)
        deliverables = self._release_deliverables(
            base_rows=base.get("deliverables", []),
            execution_plan=execution_plan,
            evidence=evidence,
            release=release,
        )
        benchmark_targets = self._release_benchmark_targets(
            base_rows=base.get("benchmark_targets", []),
            release=release,
        )
        honest_boundary = (
            "Current strength is evidence-backed planning, governance framing, and packaged delivery. "
            "It is not yet a leaderboard winner on web navigation or code-fix benchmarks because the repo "
            "still lacks full browser-actuation loops and code-task specific execution traces."
        )
        base.update(
            {
                "target_users": target_users[:5],
                "review_questions": review_questions,
                "execution_tracks": self._release_execution_tracks(proposal=proposal, execution_plan=execution_plan),
                "deliverables": deliverables,
                "benchmark_targets": benchmark_targets,
                "decision": {
                    "status": release.get("decision", "block"),
                    "reason": _clean_text(release.get("reason", "")),
                    "selected_candidate": _clean_text(release.get("selected_candidate", "")),
                    "value_index": float(run_summary.get("value_card", {}).get("value_index", 0.0)),
                },
                "honest_boundary": honest_boundary,
                "release_context": {
                    "scenario_name": _clean_text(scenario.get("name", "")),
                    "theme": _clean_text(story.get("theme", "")),
                    "headline": _clean_text(proposal.get("headline", "")),
                },
            }
        )
        return base

    @staticmethod
    def _runtime_deliverables(
        profile: MissionProfile,
        final_answer: str,
        execution_plan: list[str],
        evidence: dict[str, Any],
        live: dict[str, Any],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in profile.deliverables:
            signal = ""
            lowered = item.title.lower()
            if "evidence" in lowered:
                signal = f"{int(evidence.get('record_count', 0))} records / {int(evidence.get('citation_count', 0))} citations"
            elif "execution" in lowered or "playbook" in lowered or "timeline" in lowered or "migration" in lowered:
                signal = f"{len(execution_plan)} execution steps"
            elif "benchmark" in lowered or "validation" in lowered:
                signal = "benchmark family mapped"
            elif "decision" in lowered or "brief" in lowered or "spec" in lowered:
                signal = final_answer[:120] or "runtime answer available"
            rows.append(
                {
                    **item.to_dict(),
                    "status": "ready" if final_answer else "draft",
                    "evidence_hint": _clean_text(signal),
                    "live_backed": bool(live.get("success", False)),
                }
            )
        return rows

    @staticmethod
    def _runtime_execution_tracks(
        execution_plan: list[str],
        security: dict[str, Any],
        evidence: dict[str, Any],
    ) -> list[dict[str, Any]]:
        tracks: list[dict[str, Any]] = []
        buckets = [
            ("Track 1", execution_plan[:2]),
            ("Track 2", execution_plan[2:4]),
            ("Track 3", execution_plan[4:6]),
        ]
        for name, rows in buckets:
            if not rows:
                continue
            tracks.append(
                {
                    "name": name,
                    "focus": ", ".join(rows[:2]),
                    "success": (
                        f"preflight={security.get('preflight_action', '')}; "
                        f"evidence={int(evidence.get('record_count', 0))} records"
                    ),
                }
            )
        return tracks

    @staticmethod
    def _runtime_benchmark_targets(
        profile: MissionProfile,
        completed: bool,
        live: dict[str, Any],
        selected_skills: list[Any],
    ) -> list[dict[str, Any]]:
        rows = [item.to_dict() for item in profile.benchmark_targets]
        for row in rows:
            row["current_status"] = "mapped"
            row["current_signal"] = "runtime completed" if completed else "runtime incomplete"
            if row["name"] in {"WebArena", "SWE-bench Verified"}:
                row["current_signal"] = "not yet directly exercised"
            if bool(live.get("success", False)):
                row["current_signal"] += "; live model path exercised"
            if selected_skills:
                row["current_signal"] += f"; skills={len(selected_skills)}"
        return rows

    @staticmethod
    def _runtime_boundary(profile: MissionProfile) -> str:
        if profile.name == "implementation_pack":
            return (
                "Current implementation missions can produce specs, migration plans, and validation checklists, "
                "but they are not yet equivalent to a full code-repair benchmark loop."
            )
        if profile.name == "research_pack":
            return (
                "Current research missions are strong on packaging evidence and promotion logic, "
                "but still need public benchmark execution history to claim superiority."
            )
        return (
            "Current strength is packaging execution, evidence, and review structure in one runtime artifact. "
            "It is weaker on environments that require full browser or repository action loops."
        )

    @staticmethod
    def _release_deliverables(
        base_rows: list[dict[str, Any]],
        execution_plan: list[str],
        evidence: dict[str, Any],
        release: dict[str, Any],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in base_rows:
            row = dict(item)
            title = str(row.get("title", "")).lower()
            if "benchmark" in title or "validation" in title:
                row["evidence_hint"] = _clean_text(release.get("decision", "block"))
            elif "evidence" in title:
                row["evidence_hint"] = f"{int(evidence.get('record_count', 0))} records / {int(evidence.get('citation_count', 0))} citations"
            elif "execution" in title or "playbook" in title or "timeline" in title:
                row["evidence_hint"] = f"{len(execution_plan)} execution steps"
            row["status"] = "ready" if execution_plan else row.get("status", "draft")
            rows.append(row)
        return rows

    @staticmethod
    def _release_execution_tracks(proposal: dict[str, Any], execution_plan: list[str]) -> list[dict[str, Any]]:
        phases = proposal.get("phases", []) if isinstance(proposal, dict) else []
        tracks: list[dict[str, Any]] = []
        for phase in phases[:3]:
            tracks.append(
                {
                    "name": _clean_text(phase.get("phase", "Execution Track")),
                    "focus": _clean_text(", ".join(phase.get("actions", [])[:2])),
                    "success": _clean_text(", ".join(phase.get("success_metrics", [])[:3])),
                }
            )
        if tracks:
            return tracks
        for index, item in enumerate(execution_plan[:3], start=1):
            tracks.append(
                {
                    "name": f"Track {index}",
                    "focus": item,
                    "success": "Completed with trace, evidence, and reviewable outputs.",
                }
            )
        return tracks

    @staticmethod
    def _release_benchmark_targets(
        base_rows: list[dict[str, Any]],
        release: dict[str, Any],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in base_rows:
            row = dict(item)
            row["current_status"] = "mapped"
            row["current_signal"] = (
                "release-gated with evidence"
                if row.get("name", "") in {"GAIA", "TAU-bench", "TheAgentCompany"}
                else "partially covered"
            )
            if release:
                row["current_signal"] += f"; release={release.get('decision', 'block')}"
            rows.append(row)
        return rows

    @staticmethod
    def _defaults() -> list[MissionProfile]:
        return [
            MissionProfile(
                name="strategy_pack",
                title="Strategy Mission Pack",
                summary="Business-facing package for launch, rollout, and investment decisions.",
                primary_deliverable="Launch strategy packet with execution, evidence, and release gate.",
                target_users=["product lead", "operations lead", "risk owner", "executive sponsor"],
                output_views=["proposal", "execution plan", "evidence packet", "benchmark positioning"],
                review_questions=[
                    "Is the chosen wedge narrow enough to execute and large enough to matter?",
                    "Which release gate blocks expansion first?",
                    "What evidence is still missing for executive sign-off?",
                ],
                deliverables=[
                    MissionDeliverableBlueprint("Decision Memo", "One-page business recommendation with tradeoffs and target wedge.", "executive sponsor"),
                    MissionDeliverableBlueprint("Execution Playbook", "Phased rollout with operators, checkpoints, and fallback path.", "product and operations"),
                    MissionDeliverableBlueprint("Evidence Packet", "Citations, policy references, and runtime signals behind the claim.", "risk and procurement"),
                    MissionDeliverableBlueprint("Interop Export", "External skill-compatible bundle for downstream ecosystems.", "platform team"),
                ],
                benchmark_targets=[
                    BenchmarkTargetBlueprint("GAIA", "medium", "Good match for evidence-backed multi-step reasoning.", "Needs stronger open-web retrieval verification."),
                    BenchmarkTargetBlueprint("TAU-bench", "high", "Strong fit for enterprise workflow planning and tool orchestration.", "Needs deeper real connector coverage."),
                    BenchmarkTargetBlueprint("TheAgentCompany", "medium", "Good fit for knowledge-work packaging and operating decisions.", "Needs richer long-horizon workplace state."),
                ],
                keyword_patterns=[r"(launch|rollout|strategy|board|proposal|market|growth|copilot|enterprise|plan)"],
            ),
            MissionProfile(
                name="research_pack",
                title="Research Mission Pack",
                summary="Research-facing package for study design, evidence review, and promotion decisions.",
                primary_deliverable="Research promotion packet with experiment rationale, evidence, and release criteria.",
                target_users=["research lead", "applied scientist", "review committee"],
                output_views=["research brief", "benchmark report", "promotion packet", "risk register"],
                review_questions=[
                    "Is the claimed gain reproducible beyond the current scenario set?",
                    "Which missing evidence would most likely change the promotion decision?",
                    "What post-launch monitoring is required to validate the lab result?",
                ],
                deliverables=[
                    MissionDeliverableBlueprint("Research Brief", "Hypothesis, operating thesis, and study implications.", "research committee"),
                    MissionDeliverableBlueprint("Benchmark Readout", "Release gate, leaderboard, and evidence trail.", "lab leadership"),
                    MissionDeliverableBlueprint("Promotion Checklist", "What must pass before the result becomes default.", "release committee"),
                    MissionDeliverableBlueprint("Evidence Packet", "External and internal citations linked to the claim.", "reviewers"),
                ],
                benchmark_targets=[
                    BenchmarkTargetBlueprint("GAIA", "high", "Reasoning + retrieval alignment is directly relevant.", "Needs public benchmark execution history."),
                    BenchmarkTargetBlueprint("TheAgentCompany", "medium", "Useful for broader knowledge-work research tasks.", "Needs richer interactive environment state."),
                    BenchmarkTargetBlueprint("WebArena", "low", "Only partial overlap through retrieval and action planning.", "Needs real browser action loops."),
                ],
                keyword_patterns=[r"(research|study|paper|benchmark|experiment|lab|evaluation|hypothesis)"],
            ),
            MissionProfile(
                name="operations_pack",
                title="Operations Mission Pack",
                summary="Operations-facing package for daily execution, dependency control, and governance checkpoints.",
                primary_deliverable="Operational playbook with owners, checkpoints, and escalation paths.",
                target_users=["ops manager", "program manager", "service owner"],
                output_views=["playbook", "timeline", "dependency map", "risk register"],
                review_questions=[
                    "Which dependency can stall execution first?",
                    "Where does human override enter the loop?",
                    "What is the rollback path if live metrics degrade?",
                ],
                deliverables=[
                    MissionDeliverableBlueprint("Operational Playbook", "Practical sequence of actions and handoffs.", "delivery owner"),
                    MissionDeliverableBlueprint("Dependency Timeline", "Critical path and checkpoint plan.", "program manager"),
                    MissionDeliverableBlueprint("Risk Register", "Failure modes, control points, and escalation logic.", "ops lead"),
                    MissionDeliverableBlueprint("Evidence Packet", "Policy and runtime evidence for auditability.", "governance"),
                ],
                benchmark_targets=[
                    BenchmarkTargetBlueprint("TAU-bench", "high", "Best fit for enterprise task flow and tool-mediated work.", "Needs live business connectors."),
                    BenchmarkTargetBlueprint("TheAgentCompany", "medium", "Useful for workplace productivity packaging.", "Needs persistent workplace memory."),
                    BenchmarkTargetBlueprint("GAIA", "low", "Only partial overlap via multi-hop reasoning.", "Less relevant than ops execution fidelity."),
                ],
                keyword_patterns=[r"(ops|operations|timeline|delivery|program|workflow|dependency|playbook|milestone)"],
            ),
            MissionProfile(
                name="implementation_pack",
                title="Implementation Mission Pack",
                summary="Engineering-facing package for architecture, migration, and validation planning.",
                primary_deliverable="Implementation spec with architecture target state, migration steps, and validation gates.",
                target_users=["tech lead", "staff engineer", "platform owner"],
                output_views=["architecture spec", "migration plan", "validation checklist", "risk register"],
                review_questions=[
                    "What execution trace proves the design is implementable?",
                    "Which integration or operability gap is still unowned?",
                    "What benchmark should validate the implementation class?",
                ],
                deliverables=[
                    MissionDeliverableBlueprint("Architecture Spec", "Target state and integration blueprint.", "tech lead"),
                    MissionDeliverableBlueprint("Migration Plan", "Phased delivery path with rollback boundary.", "platform team"),
                    MissionDeliverableBlueprint("Validation Checklist", "Tests, evals, and release gates for implementation.", "engineering manager"),
                    MissionDeliverableBlueprint("Benchmark Mapping", "Which benchmark family actually matters for this build.", "research and engineering"),
                ],
                benchmark_targets=[
                    BenchmarkTargetBlueprint("SWE-bench Verified", "medium", "Relevant once the system closes the code-fix loop.", "Current engine is not yet a code-repair benchmark runner."),
                    BenchmarkTargetBlueprint("WebArena", "low", "Relevant for integration flows with heavy browser action.", "Missing real browser execution layer."),
                    BenchmarkTargetBlueprint("GAIA", "medium", "Useful for architecture reasoning quality.", "Not sufficient for implementation proof."),
                ],
                keyword_patterns=[r"(architecture|design|system|integration|refactor|migration|implementation|build|code)"],
            ),
        ]
