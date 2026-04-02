"""Tool manifest and capability catalog for harness discovery/governance."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.harness.models import ToolType


@dataclass
class HarnessToolManifest:
    """Capability declaration for one harness tool."""

    name: str
    tool_type: ToolType
    summary: str
    provider: str = "core"
    version: str = "1.0.0"
    tags: list[str] = field(default_factory=list)
    intents: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    risk_level: str = "medium"
    default_args: dict[str, Any] = field(default_factory=dict)
    write_actions: bool = False
    network_actions: bool = False
    code_execution: bool = False
    cost_score: float = 1.0
    latency_score: float = 1.0
    reliability_score: float = 0.85
    novelty_score: float = 0.5
    compatible_with: list[str] = field(default_factory=list)
    guardrail_profile: list[str] = field(default_factory=list)
    external_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tool_type"] = self.tool_type.value
        return payload


class ToolManifestRegistry:
    """Registry of harness tool manifests."""

    def __init__(self, manifests: list[HarnessToolManifest] | None = None) -> None:
        self._registry: dict[str, HarnessToolManifest] = {}
        for item in self._default_manifests():
            self._registry[item.name] = item
        for item in manifests or []:
            self._registry[item.name] = item

    def register(self, manifest: HarnessToolManifest) -> None:
        self._registry[manifest.name] = manifest

    def get(self, name: str) -> HarnessToolManifest | None:
        return self._registry.get(name)

    def list_all(self) -> list[HarnessToolManifest]:
        return [self._registry[name] for name in sorted(self._registry.keys())]

    def as_catalog(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.list_all()]

    @staticmethod
    def _default_manifests() -> list[HarnessToolManifest]:
        return [
            HarnessToolManifest(
                name="api_market_discover",
                tool_type=ToolType.API,
                summary="Discover marketplace skills relevant to user query.",
                tags=["marketplace", "skill", "discovery", "ranking"],
                intents=["discovery", "comparison", "research"],
                capabilities=["search", "ranking", "relevance"],
                risk_level="low",
                default_args={"limit": 4},
                cost_score=0.8,
                latency_score=0.7,
                reliability_score=0.9,
                novelty_score=0.7,
                compatible_with=["code_skill_search", "policy_risk_matrix"],
                guardrail_profile=["read_only"],
                external_refs=["https://github.com/trending?since=weekly"],
            ),
            HarnessToolManifest(
                name="browser_trending_scan",
                tool_type=ToolType.BROWSER,
                summary="Scan trending skills and ecosystem signals.",
                tags=["trending", "ecosystem", "browser", "signals"],
                intents=["research", "scouting", "innovation"],
                capabilities=["trending_scan", "landscape_mapping"],
                risk_level="medium",
                default_args={"limit": 4},
                network_actions=True,
                cost_score=1.0,
                latency_score=1.2,
                reliability_score=0.8,
                novelty_score=0.9,
                compatible_with=["ecosystem_provider_radar", "external_resource_hub"],
                guardrail_profile=["network_read_only"],
                external_refs=["https://github.com/trending?since=weekly"],
            ),
            HarnessToolManifest(
                name="code_skill_search",
                tool_type=ToolType.CODE,
                summary="Search local and external skills by capability and intent.",
                tags=["codebase", "skills", "introspection", "matching"],
                intents=["implementation", "analysis", "discovery"],
                capabilities=["registry_search", "metadata_filtering"],
                risk_level="low",
                default_args={"limit": 8},
                cost_score=0.8,
                latency_score=0.5,
                reliability_score=0.95,
                novelty_score=0.6,
                compatible_with=["api_skill_dependency_graph", "policy_risk_matrix"],
                guardrail_profile=["read_only"],
            ),
            HarnessToolManifest(
                name="policy_risk_matrix",
                tool_type=ToolType.CODE,
                summary="Build multi-dimension risk matrix and control suggestions.",
                tags=["risk", "policy", "governance", "audit", "compliance"],
                intents=["risk", "audit", "compliance", "safety"],
                capabilities=["risk_classification", "control_mapping"],
                risk_level="low",
                default_args={},
                cost_score=1.0,
                latency_score=0.6,
                reliability_score=0.9,
                novelty_score=0.8,
                compatible_with=["api_market_discover", "api_skill_dependency_graph"],
                guardrail_profile=["read_only", "safety_aligned"],
                external_refs=["https://modelcontextprotocol.io/specification/2025-06-18/architecture/index"],
            ),
            HarnessToolManifest(
                name="memory_context_digest",
                tool_type=ToolType.CODE,
                summary="Summarize prior harness memory events into reusable context.",
                tags=["memory", "context", "state", "continuity"],
                intents=["context", "recovery", "planning"],
                capabilities=["session_summary", "state_reuse"],
                risk_level="low",
                default_args={"limit": 8},
                cost_score=0.6,
                latency_score=0.4,
                reliability_score=0.92,
                novelty_score=0.5,
                compatible_with=["policy_risk_matrix", "code_skill_search"],
                guardrail_profile=["read_only"],
                external_refs=["https://docs.langchain.com/oss/python/langgraph/overview"],
            ),
            HarnessToolManifest(
                name="ecosystem_provider_radar",
                tool_type=ToolType.API,
                summary="Aggregate ecosystem providers and strength signals.",
                tags=["provider", "ecosystem", "reputation", "landscape"],
                intents=["research", "selection", "comparison"],
                capabilities=["provider_analytics", "reputation_stats"],
                risk_level="low",
                default_args={"limit": 5},
                cost_score=0.9,
                latency_score=0.8,
                reliability_score=0.86,
                novelty_score=0.75,
                compatible_with=["browser_trending_scan", "api_market_discover"],
                guardrail_profile=["read_only"],
            ),
            HarnessToolManifest(
                name="external_resource_hub",
                tool_type=ToolType.BROWSER,
                summary="Recommend external references aligned to query intent.",
                tags=["resources", "references", "docs", "mcp", "langgraph"],
                intents=["research", "learning", "design"],
                capabilities=["curated_references", "hotspot_mapping"],
                risk_level="medium",
                default_args={"limit": 5},
                network_actions=True,
                cost_score=0.7,
                latency_score=0.5,
                reliability_score=0.87,
                novelty_score=0.95,
                compatible_with=["browser_trending_scan", "policy_risk_matrix"],
                guardrail_profile=["network_read_only"],
                external_refs=[
                    "https://modelcontextprotocol.io/specification/2025-06-18/architecture/index",
                    "https://docs.langchain.com/oss/python/langgraph/overview",
                ],
            ),
            HarnessToolManifest(
                name="api_skill_dependency_graph",
                tool_type=ToolType.API,
                summary="Extract compatibility/synergy graph across available skills.",
                tags=["dependency", "graph", "synergy", "router"],
                intents=["analysis", "planning", "orchestration"],
                capabilities=["skill_graph", "compatibility_analysis"],
                risk_level="low",
                default_args={"limit": 20},
                cost_score=1.2,
                latency_score=0.8,
                reliability_score=0.9,
                novelty_score=0.85,
                compatible_with=["code_skill_search", "policy_risk_matrix"],
                guardrail_profile=["read_only"],
            ),
            HarnessToolManifest(
                name="code_router_blueprint",
                tool_type=ToolType.CODE,
                summary="Generate architecture blueprint for router/harness evolution.",
                tags=["architecture", "blueprint", "roadmap", "design"],
                intents=["implementation", "design", "optimization"],
                capabilities=["blueprinting", "modularization"],
                risk_level="low",
                default_args={},
                code_execution=True,
                cost_score=1.1,
                latency_score=0.7,
                reliability_score=0.83,
                novelty_score=0.92,
                compatible_with=["memory_context_digest", "api_skill_dependency_graph"],
                guardrail_profile=["code_read_only"],
            ),
            HarnessToolManifest(
                name="api_skill_portfolio_optimizer",
                tool_type=ToolType.API,
                summary="Build a multi-objective portfolio of skills for daily execution tasks.",
                tags=["portfolio", "optimization", "daily", "planning", "analysis"],
                intents=["planning", "comparison", "research"],
                capabilities=["multi_objective_ranking", "provider_diversity", "risk_cost_tradeoff"],
                risk_level="low",
                default_args={"limit": 5, "risk_tolerance": "medium"},
                cost_score=0.9,
                latency_score=0.9,
                reliability_score=0.9,
                novelty_score=0.82,
                compatible_with=["policy_risk_matrix", "memory_context_digest", "ecosystem_provider_radar"],
                guardrail_profile=["read_only", "safety_aligned"],
            ),
            HarnessToolManifest(
                name="code_experiment_design",
                tool_type=ToolType.CODE,
                summary="Design reproducible ablation and benchmark plans for research-grade evaluation.",
                tags=["research", "benchmark", "ablation", "evaluation", "design"],
                intents=["research", "design", "analysis"],
                capabilities=["hypothesis_design", "metric_selection", "validity_analysis"],
                risk_level="low",
                default_args={"max_experiments": 6},
                code_execution=True,
                cost_score=0.8,
                latency_score=0.6,
                reliability_score=0.88,
                novelty_score=0.94,
                compatible_with=["external_resource_hub", "api_skill_dependency_graph", "code_router_blueprint"],
                guardrail_profile=["code_read_only"],
                external_refs=[
                    "https://github.com/princeton-nlp/SWE-agent",
                    "https://github.com/SWE-bench/SWE-bench",
                ],
            ),
        ]
