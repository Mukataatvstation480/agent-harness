"""Composable harness recipes (workflow blueprints)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RecipeStep:
    """One step in a harness workflow recipe."""

    step_id: str
    title: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    when_any_keywords: list[str] = field(default_factory=list)
    when_all_keywords: list[str] = field(default_factory=list)
    fallback_tools: list[str] = field(default_factory=list)
    optional: bool = False
    parallel_group: str = ""

    def applicable(self, query: str) -> bool:
        lowered = query.lower()
        if self.when_all_keywords and not all(item.lower() in lowered for item in self.when_all_keywords):
            return False
        if self.when_any_keywords and not any(item.lower() in lowered for item in self.when_any_keywords):
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["id"] = payload.pop("step_id")
        return payload


@dataclass
class HarnessRecipe:
    """A multi-step workflow recipe used by harness engine."""

    name: str
    version: str
    description: str
    tags: list[str] = field(default_factory=list)
    default_mode: str = "balanced"
    steps: list[RecipeStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "default_mode": self.default_mode,
            "steps": [step.to_dict() for step in self.steps],
        }


class RecipeRegistry:
    """Built-in and file-based recipe loader."""

    def __init__(self) -> None:
        self._recipes: dict[str, HarnessRecipe] = {}
        for item in self._default_recipes():
            self._recipes[item.name] = item

    def list_recipes(self) -> list[HarnessRecipe]:
        return [self._recipes[name] for name in sorted(self._recipes.keys())]

    def list_recipe_cards(self) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        for recipe in self.list_recipes():
            cards.append(
                {
                    "name": recipe.name,
                    "version": recipe.version,
                    "description": recipe.description,
                    "tags": recipe.tags,
                    "default_mode": recipe.default_mode,
                    "steps": len(recipe.steps),
                }
            )
        return cards

    def get(self, name: str) -> HarnessRecipe | None:
        return self._recipes.get(name)

    def suggest(self, query: str) -> HarnessRecipe | None:
        lowered = query.lower()
        if any(token in lowered for token in ["risk", "audit", "compliance", "safety"]):
            return self._recipes.get("risk-radar")
        if any(token in lowered for token in ["enterprise", "stakeholder", "board", "communication", "governance"]):
            return self._recipes.get("enterprise-ops")
        if any(token in lowered for token in ["daily", "routine", "todo", "meeting", "workflow", "productivity"]):
            return self._recipes.get("daily-operator")
        if any(token in lowered for token in ["benchmark", "ablation", "experiment", "reproducible", "paper"]):
            return self._recipes.get("research-rig")
        if any(token in lowered for token in ["creative", "brand", "design", "visual", "campaign", "presentation"]):
            return self._recipes.get("creative-studio")
        if any(token in lowered for token in ["ecosystem", "market", "provider", "trend"]):
            return self._recipes.get("ecosystem-hunter")
        if any(token in lowered for token in ["code", "architecture", "refactor", "router"]):
            return self._recipes.get("router-forge")
        return None

    def load_from_file(self, path: str | Path) -> HarnessRecipe:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Recipe file not found: {file_path}")

        raw = file_path.read_text(encoding="utf-8")
        if file_path.suffix.lower() == ".json":
            payload = json.loads(raw)
            return self._from_dict(payload)

        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency path
            raise ValueError("Only JSON recipes are supported unless PyYAML is installed.") from exc

        payload = yaml.safe_load(raw)
        return self._from_dict(payload)

    def register(self, recipe: HarnessRecipe) -> None:
        self._recipes[recipe.name] = recipe

    def _from_dict(self, payload: dict[str, Any]) -> HarnessRecipe:
        steps_raw = payload.get("steps", [])
        steps: list[RecipeStep] = []
        for index, item in enumerate(steps_raw):
            steps.append(
                RecipeStep(
                    step_id=str(item.get("id", f"step-{index + 1}")),
                    title=str(item.get("title", f"Step {index + 1}")),
                    tool=str(item.get("tool", "")),
                    args=dict(item.get("args", {})),
                    when_any_keywords=[str(x) for x in item.get("when_any_keywords", [])],
                    when_all_keywords=[str(x) for x in item.get("when_all_keywords", [])],
                    fallback_tools=[str(x) for x in item.get("fallback_tools", [])],
                    optional=bool(item.get("optional", False)),
                    parallel_group=str(item.get("parallel_group", "")),
                )
            )

        return HarnessRecipe(
            name=str(payload.get("name", "custom-recipe")),
            version=str(payload.get("version", "1.0.0")),
            description=str(payload.get("description", "User-provided recipe")),
            tags=[str(x) for x in payload.get("tags", [])],
            default_mode=str(payload.get("default_mode", "balanced")),
            steps=steps,
        )

    @staticmethod
    def _default_recipes() -> list[HarnessRecipe]:
        return [
            HarnessRecipe(
                name="risk-radar",
                version="1.0.0",
                description="Governance-first workflow for risky or compliance-sensitive tasks.",
                tags=["risk", "compliance", "audit"],
                default_mode="safety_critical",
                steps=[
                    RecipeStep(
                        step_id="scan-market",
                        title="Collect relevant external skills",
                        tool="api_market_discover",
                        args={"limit": 4},
                    ),
                    RecipeStep(
                        step_id="risk-matrix",
                        title="Generate structured risk matrix",
                        tool="policy_risk_matrix",
                        args={},
                    ),
                    RecipeStep(
                        step_id="dependency-graph",
                        title="Analyze skill dependency and conflict graph",
                        tool="api_skill_dependency_graph",
                        args={"limit": 15},
                        fallback_tools=["code_skill_search"],
                    ),
                    RecipeStep(
                        step_id="external-references",
                        title="Attach external references for traceability",
                        tool="external_resource_hub",
                        args={"limit": 5},
                        optional=True,
                    ),
                ],
            ),
            HarnessRecipe(
                name="ecosystem-hunter",
                version="1.0.0",
                description="Landscape scouting workflow focused on providers and trending capabilities.",
                tags=["ecosystem", "trending", "innovation"],
                default_mode="deep",
                steps=[
                    RecipeStep(
                        step_id="trending",
                        title="Scan trending capabilities",
                        tool="browser_trending_scan",
                        args={"limit": 6},
                    ),
                    RecipeStep(
                        step_id="provider-radar",
                        title="Rank high-signal providers",
                        tool="ecosystem_provider_radar",
                        args={"limit": 5},
                    ),
                    RecipeStep(
                        step_id="skill-search",
                        title="Search local/external skill fit",
                        tool="code_skill_search",
                        args={"limit": 10},
                    ),
                    RecipeStep(
                        step_id="resource-brief",
                        title="Return latest references",
                        tool="external_resource_hub",
                        args={"limit": 6},
                    ),
                ],
            ),
            HarnessRecipe(
                name="router-forge",
                version="1.0.0",
                description="Build a practical optimization blueprint for router/harness evolution.",
                tags=["code", "architecture", "optimization"],
                default_mode="balanced",
                steps=[
                    RecipeStep(
                        step_id="context",
                        title="Summarize session context",
                        tool="memory_context_digest",
                        args={"limit": 12},
                    ),
                    RecipeStep(
                        step_id="search-skills",
                        title="Locate matching skill capabilities",
                        tool="code_skill_search",
                        args={"limit": 10},
                    ),
                    RecipeStep(
                        step_id="dependency",
                        title="Map dependencies and synergies",
                        tool="api_skill_dependency_graph",
                        args={"limit": 18},
                    ),
                    RecipeStep(
                        step_id="blueprint",
                        title="Generate architecture blueprint",
                        tool="code_router_blueprint",
                        args={},
                        fallback_tools=["policy_risk_matrix"],
                    ),
                ],
            ),
            HarnessRecipe(
                name="daily-operator",
                version="1.0.0",
                description="Daily operations workflow for practical planning, prioritization, and controls.",
                tags=["daily", "operations", "productivity"],
                default_mode="balanced",
                steps=[
                    RecipeStep(
                        step_id="context-digest",
                        title="Digest recent context and execution behavior",
                        tool="memory_context_digest",
                        args={"limit": 12},
                    ),
                    RecipeStep(
                        step_id="portfolio-plan",
                        title="Build multi-objective skill portfolio for the current task",
                        tool="api_skill_portfolio_optimizer",
                        args={"limit": 5, "risk_tolerance": "medium"},
                    ),
                    RecipeStep(
                        step_id="risk-check",
                        title="Apply practical risk-control matrix before final recommendation",
                        tool="policy_risk_matrix",
                        args={},
                    ),
                    RecipeStep(
                        step_id="execution-blueprint",
                        title="Generate concise execution blueprint",
                        tool="code_router_blueprint",
                        args={},
                        optional=True,
                    ),
                ],
            ),
            HarnessRecipe(
                name="research-rig",
                version="1.0.0",
                description="Research-oriented workflow for benchmark design and reproducible experiments.",
                tags=["research", "benchmark", "ablation"],
                default_mode="deep",
                steps=[
                    RecipeStep(
                        step_id="trend-scan",
                        title="Collect ecosystem trend signals for baselines",
                        tool="browser_trending_scan",
                        args={"limit": 6},
                    ),
                    RecipeStep(
                        step_id="reference-pack",
                        title="Attach external references and benchmark anchors",
                        tool="external_resource_hub",
                        args={"limit": 6},
                    ),
                    RecipeStep(
                        step_id="experiment-design",
                        title="Design ablation matrix and evaluation protocol",
                        tool="code_experiment_design",
                        args={"max_experiments": 6},
                    ),
                    RecipeStep(
                        step_id="dependency-model",
                        title="Map dependency graph for candidate skill stacks",
                        tool="api_skill_dependency_graph",
                        args={"limit": 20},
                        optional=True,
                    ),
                ],
            ),
            HarnessRecipe(
                name="creative-studio",
                version="1.0.0",
                description="Creative workflow for concept shaping and visual storytelling direction.",
                tags=["creative", "design", "presentation"],
                default_mode="balanced",
                steps=[
                    RecipeStep(
                        step_id="trend-inspiration",
                        title="Scan recent trends for inspiration and references",
                        tool="browser_trending_scan",
                        args={"limit": 6},
                    ),
                    RecipeStep(
                        step_id="portfolio-ideas",
                        title="Select best-fit skill portfolio for creative execution",
                        tool="api_skill_portfolio_optimizer",
                        args={"limit": 5, "risk_tolerance": "medium"},
                    ),
                    RecipeStep(
                        step_id="concept-blueprint",
                        title="Generate concept-to-execution blueprint",
                        tool="code_router_blueprint",
                        args={},
                    ),
                    RecipeStep(
                        step_id="references",
                        title="Attach reference links for rationale and reuse",
                        tool="external_resource_hub",
                        args={"limit": 4},
                        optional=True,
                    ),
                ],
            ),
            HarnessRecipe(
                name="enterprise-ops",
                version="1.0.0",
                description="Enterprise-friendly workflow focused on stakeholder alignment and safety controls.",
                tags=["enterprise", "governance", "stakeholder"],
                default_mode="safety_critical",
                steps=[
                    RecipeStep(
                        step_id="context",
                        title="Digest recent execution context and continuity signals",
                        tool="memory_context_digest",
                        args={"limit": 10},
                    ),
                    RecipeStep(
                        step_id="risk-controls",
                        title="Apply structured enterprise risk-control matrix",
                        tool="policy_risk_matrix",
                        args={},
                    ),
                    RecipeStep(
                        step_id="portfolio",
                        title="Optimize skill portfolio under lower risk tolerance",
                        tool="api_skill_portfolio_optimizer",
                        args={"limit": 5, "risk_tolerance": "low"},
                    ),
                    RecipeStep(
                        step_id="dependency",
                        title="Map dependencies and integration conflicts",
                        tool="api_skill_dependency_graph",
                        args={"limit": 16},
                        optional=True,
                    ),
                ],
            ),
        ]
