"""Scenario-aware proposal defaults for task execution planning."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProposalPillarBlueprint:
    title: str
    summary: str
    integration: str
    live_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "summary": self.summary,
            "integration": self.integration,
            "live_key": self.live_key,
        }


@dataclass(frozen=True)
class ProposalPhaseBlueprint:
    phase: str
    actions: list[str]
    success_metrics: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "actions": list(self.actions),
            "success_metrics": list(self.success_metrics),
        }


@dataclass(frozen=True)
class ProposalScenario:
    name: str
    theme: str
    release_need: str
    audience_takeaway: str
    headline: str
    strategy_plan: list[str]
    business_summary: list[str]
    critical_risks: list[str]
    impact_labels: list[str]
    keyword_patterns: list[str] = field(default_factory=list)
    pillars: list[ProposalPillarBlueprint] = field(default_factory=list)
    phases: list[ProposalPhaseBlueprint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "theme": self.theme,
            "release_need": self.release_need,
            "audience_takeaway": self.audience_takeaway,
            "headline": self.headline,
            "strategy_plan": list(self.strategy_plan),
            "business_summary": list(self.business_summary),
            "critical_risks": list(self.critical_risks),
            "impact_labels": list(self.impact_labels),
            "keyword_patterns": list(self.keyword_patterns),
            "pillars": [item.to_dict() for item in self.pillars],
            "phases": [item.to_dict() for item in self.phases],
        }


class ProposalRegistry:
    """Infer a concrete business scenario and provide proposal defaults."""

    def __init__(self) -> None:
        self._scenarios = self._defaults()

    def infer(self, query: str) -> ProposalScenario:
        text = query.lower().strip()
        best = self._scenarios[-1]
        best_score = -1
        for scenario in self._scenarios:
            score = sum(1 for pattern in scenario.keyword_patterns if re.search(pattern, text))
            if score > best_score:
                best = scenario
                best_score = score
        return best

    def list_cards(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self._scenarios]

    @staticmethod
    def _defaults() -> list[ProposalScenario]:
        return [
            ProposalScenario(
                name="research_ops",
                theme="Delivering research-grade evidence and analysis with operational rigor.",
                release_need=(
                    "A team needs a plan that moves from investigation through evidence collection "
                    "to actionable findings with quality gates."
                ),
                audience_takeaway="A structured research pipeline with evidence anchors and decision readiness.",
                headline="Research and Evidence Delivery Plan",
                strategy_plan=[
                    "Frame the core question and define what evidence would answer it.",
                    "Collect and validate evidence before drawing conclusions.",
                    "Package findings into actionable deliverables with clear next steps.",
                ],
                business_summary=[
                    "Start with a focused question and measurable success criteria.",
                    "Build evidence incrementally with quality checks at each stage.",
                    "Convert findings into decision-ready artifacts.",
                ],
                critical_risks=[
                    "Evidence quality is too thin to support the conclusion.",
                    "Scope creep dilutes the core question.",
                    "Findings are not actionable without further work.",
                ],
                impact_labels=["Evidence quality", "Decision readiness", "Execution clarity", "Risk visibility"],
                keyword_patterns=[
                    r"(research|study|experiment|evidence|analysis|investigate|evaluate)",
                    r"(improvement|upgrade|roadmap|gaps|standards|deep research)",
                ],
                pillars=[
                    ProposalPillarBlueprint("Evidence Pipeline", "Systematic evidence collection and validation.", "Feeds into decision artifacts.", "research_pillar"),
                    ProposalPillarBlueprint("Quality Gates", "Review and validation checkpoints.", "Prevents premature conclusions.", "governance_pillar"),
                    ProposalPillarBlueprint("Decision Readout", "Actionable findings for stakeholders.", "Translates evidence into action.", "growth_pillar"),
                ],
                phases=[
                    ProposalPhaseBlueprint("Phase 1 - Frame", ["Define the core question.", "Identify evidence sources and success criteria."], ["question defined", "evidence plan ready"]),
                    ProposalPhaseBlueprint("Phase 2 - Investigate", ["Collect and validate evidence.", "Run analysis and synthesis."], ["evidence collected", "analysis complete"]),
                    ProposalPhaseBlueprint("Phase 3 - Deliver", ["Package findings.", "Present actionable recommendations."], ["deliverable ready", "decision review complete"]),
                ],
            ),
            ProposalScenario(
                name="implementation_plan",
                theme="Planning and executing a technical implementation with validation and risk management.",
                release_need=(
                    "A team needs a concrete implementation plan with architecture decisions, "
                    "migration steps, and validation gates."
                ),
                audience_takeaway="A phased implementation roadmap with risk mitigation and quality checkpoints.",
                headline="Implementation and Delivery Plan",
                strategy_plan=[
                    "Define the target architecture and key technical decisions upfront.",
                    "Break the work into validated phases with clear rollback boundaries.",
                    "Prove correctness through tests and evidence before expanding scope.",
                ],
                business_summary=[
                    "Start with the highest-risk technical decision and validate it first.",
                    "Use phased delivery with rollback capability at each stage.",
                    "Track quality through automated tests and manual review gates.",
                ],
                critical_risks=[
                    "Architecture assumptions are invalidated during implementation.",
                    "Integration complexity exceeds estimates.",
                    "Validation coverage is too thin to catch regressions.",
                ],
                impact_labels=["Technical correctness", "Delivery velocity", "Risk mitigation", "Quality assurance"],
                keyword_patterns=[
                    r"(implement|build|code|deploy|migrate|refactor|architecture)",
                    r"(enterprise|workflow|platform|rollout|security|operations)",
                    r"(copilot|assistant|agent|launch|plan)",
                    r"(regulated|compliance|audit|policy|governance)",
                ],
                pillars=[
                    ProposalPillarBlueprint("Architecture", "Target state and integration design.", "Foundation for all execution phases.", "growth_pillar"),
                    ProposalPillarBlueprint("Validation", "Tests, gates, and quality checks.", "Proves correctness at each phase.", "governance_pillar"),
                    ProposalPillarBlueprint("Delivery", "Phased rollout with rollback capability.", "Controls risk during execution.", "research_pillar"),
                ],
                phases=[
                    ProposalPhaseBlueprint("Phase 1 - Design", ["Define architecture and key decisions.", "Identify risks and dependencies."], ["architecture defined", "risks mapped"]),
                    ProposalPhaseBlueprint("Phase 2 - Build", ["Implement in validated phases.", "Run tests and collect evidence."], ["implementation complete", "tests passing"]),
                    ProposalPhaseBlueprint("Phase 3 - Ship", ["Deploy with monitoring.", "Validate in production."], ["deployment complete", "monitoring active"]),
                ],
            ),
            ProposalScenario(
                name="general_task",
                theme="Executing a general task with planning, evidence, and quality assurance.",
                release_need=(
                    "A team needs a concrete plan to accomplish a task with evidence-backed decisions "
                    "and measurable quality gates."
                ),
                audience_takeaway="A structured execution plan with evidence, validation, and clear deliverables.",
                headline="Task Execution Plan",
                strategy_plan=[
                    "Define scope and success criteria before starting execution.",
                    "Collect evidence and validate assumptions throughout.",
                    "Package results into reviewable deliverables.",
                ],
                business_summary=[
                    "Start with clear scope and measurable goals.",
                    "Execute in phases with validation at each checkpoint.",
                    "Deliver artifacts that stakeholders can inspect and act on.",
                ],
                critical_risks=[
                    "Scope expands faster than evidence quality.",
                    "Results are not actionable without further refinement.",
                    "Quality gates are skipped under time pressure.",
                ],
                impact_labels=["Value creation", "Quality assurance", "Execution clarity", "Risk management"],
                keyword_patterns=[],
                pillars=[
                    ProposalPillarBlueprint("Execution", "Core task delivery.", "Integrated into the delivery pipeline.", "growth_pillar"),
                    ProposalPillarBlueprint("Governance", "Quality and risk controls.", "Prevents shortcuts and regressions.", "governance_pillar"),
                    ProposalPillarBlueprint("Evidence", "Supporting data and validation.", "Backs every decision with proof.", "research_pillar"),
                ],
                phases=[
                    ProposalPhaseBlueprint("Phase 1 - Scope", ["Define the task and success criteria.", "Identify resources and risks."], ["scope defined", "plan ready"]),
                    ProposalPhaseBlueprint("Phase 2 - Execute", ["Run the plan.", "Collect evidence and validate."], ["execution complete", "evidence collected"]),
                    ProposalPhaseBlueprint("Phase 3 - Deliver", ["Package results.", "Review and hand off."], ["deliverable ready", "review complete"]),
                ],
            ),
        ]
