"""Harness tool adapters (API/browser/code-like capabilities)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from app.ecosystem.marketplace import (
    discover_for_query,
    get_provider_stats,
    get_trending_skills,
    list_marketplace_skills,
)
from app.skills.registry import list_all_skills

from app.harness.models import ToolCall, ToolResult, ToolType


class ToolRegistry:
    """Registry for harness-level tool calls."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[[dict[str, Any]], Any]] = {
            "api_market_discover": self._api_market_discover,
            "browser_trending_scan": self._browser_trending_scan,
            "code_skill_search": self._code_skill_search,
            "policy_risk_matrix": self._policy_risk_matrix,
            "memory_context_digest": self._memory_context_digest,
            "ecosystem_provider_radar": self._ecosystem_provider_radar,
            "external_resource_hub": self._external_resource_hub,
            "api_skill_dependency_graph": self._api_skill_dependency_graph,
            "code_router_blueprint": self._code_router_blueprint,
        }
        self._tool_types: dict[str, ToolType] = {
            "api_market_discover": ToolType.API,
            "browser_trending_scan": ToolType.BROWSER,
            "code_skill_search": ToolType.CODE,
            "policy_risk_matrix": ToolType.CODE,
            "memory_context_digest": ToolType.CODE,
            "ecosystem_provider_radar": ToolType.API,
            "external_resource_hub": ToolType.BROWSER,
            "api_skill_dependency_graph": ToolType.API,
            "code_router_blueprint": ToolType.CODE,
        }

    def available_tools(self) -> list[str]:
        """List all registered tools."""

        return sorted(self._tools.keys())

    def infer_tool_type(self, tool_name: str) -> ToolType:
        """Infer tool type from tool name."""

        return self._tool_types.get(tool_name, ToolType.CODE)

    def call(self, tool_call: ToolCall) -> ToolResult:
        """Execute one tool call and return standardized result."""

        start = time.time()
        fn = self._tools.get(tool_call.name)
        if not fn:
            end = time.time()
            return ToolResult(
                name=tool_call.name,
                success=False,
                output={},
                latency_ms=(end - start) * 1000.0,
                error=f"unknown_tool:{tool_call.name}",
            )

        try:
            output = fn(tool_call.args)
            success = True
            error = ""
        except Exception as exc:  # pragma: no cover - defensive
            output = {}
            success = False
            error = str(exc)
        end = time.time()

        return ToolResult(
            name=tool_call.name,
            success=success,
            output=output,
            latency_ms=(end - start) * 1000.0,
            error=error,
        )

    @staticmethod
    def _api_market_discover(args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", ""))
        limit = int(args.get("limit", 3))
        return {"matches": discover_for_query(query=query, limit=limit)}

    @staticmethod
    def _browser_trending_scan(args: dict[str, Any]) -> dict[str, Any]:
        limit = int(args.get("limit", 3))
        return {"trending": get_trending_skills(limit=limit)}

    @staticmethod
    def _code_skill_search(args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).lower()
        limit = int(args.get("limit", 8))
        matches = []
        for meta in list_all_skills():
            haystack = " ".join([meta.name, meta.description, " ".join(meta.confidence_keywords)]).lower()
            if query and query in haystack:
                matches.append(
                    {
                        "name": meta.name,
                        "category": meta.category.value,
                        "tier": meta.tier.value,
                        "cost": meta.compute_cost,
                    }
                )
        if not query:
            matches = [
                {
                    "name": meta.name,
                    "category": meta.category.value,
                    "tier": meta.tier.value,
                    "cost": meta.compute_cost,
                }
                for meta in list_all_skills()[:limit]
            ]
        return {"skills": matches[:limit]}

    @staticmethod
    def _policy_risk_matrix(args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).lower()
        dimensions = {
            "security": ["security", "attack", "credential", "secret", "token", "breach"],
            "compliance": ["compliance", "audit", "regulation", "policy", "governance", "legal"],
            "delivery": ["deadline", "timeline", "release", "milestone", "delivery", "ship"],
            "financial": ["cost", "budget", "roi", "price", "financial", "spend"],
            "reputation": ["brand", "trust", "stakeholder", "public", "reputation"],
        }
        controls = {
            "security": ["least-privilege tools", "input sanitization", "human approval for high risk"],
            "compliance": ["trace logging", "policy checklist", "evidence retention"],
            "delivery": ["milestone gating", "fallback plan", "critical path buffer"],
            "financial": ["cost cap per step", "budget checkpoint", "defer expensive tools"],
            "reputation": ["transparent rationale", "minority report", "stakeholder review"],
        }

        matrix: list[dict[str, Any]] = []
        overall_score = 0.0
        for dim, words in dimensions.items():
            hits = sum(1 for token in words if token in query)
            score = min(1.0, 0.2 + 0.2 * hits) if hits > 0 else 0.2
            if "critical" in query and dim in {"security", "compliance"}:
                score = min(1.0, score + 0.2)
            level = "low"
            if score >= 0.75:
                level = "high"
            elif score >= 0.45:
                level = "medium"
            matrix.append(
                {
                    "dimension": dim,
                    "score": round(score, 3),
                    "level": level,
                    "controls": controls[dim],
                }
            )
            overall_score += score

        overall_score /= max(len(matrix), 1)
        overall_level = "low"
        if overall_score >= 0.75:
            overall_level = "high"
        elif overall_score >= 0.45:
            overall_level = "medium"

        return {
            "risk_matrix": matrix,
            "overall_score": round(overall_score, 3),
            "overall_level": overall_level,
        }

    @staticmethod
    def _memory_context_digest(args: dict[str, Any]) -> dict[str, Any]:
        events = args.get("events", [])
        limit = int(args.get("limit", 8))
        if not isinstance(events, list):
            events = []
        sampled = events[-limit:]

        total = len(sampled)
        success_count = sum(1 for item in sampled if isinstance(item, dict) and item.get("success"))
        avg_latency = 0.0
        latency_values = [
            float(item.get("latency_ms", 0.0))
            for item in sampled
            if isinstance(item, dict) and "latency_ms" in item
        ]
        if latency_values:
            avg_latency = sum(latency_values) / len(latency_values)

        recent_tools: list[str] = []
        for item in reversed(sampled):
            if not isinstance(item, dict):
                continue
            tool = str(item.get("tool", ""))
            if tool and tool not in recent_tools:
                recent_tools.append(tool)

        return {
            "event_count": total,
            "success_rate": round(success_count / max(total, 1), 3),
            "avg_latency_ms": round(avg_latency, 2),
            "recent_tools": recent_tools[:5],
        }

    @staticmethod
    def _ecosystem_provider_radar(args: dict[str, Any]) -> dict[str, Any]:
        limit = int(args.get("limit", 5))
        all_skills = list_marketplace_skills()
        providers: list[str] = []
        for item in all_skills:
            provider = str(item.get("provider", ""))
            if provider and provider not in providers:
                providers.append(provider)
            if len(providers) >= limit:
                break

        stats = [get_provider_stats(provider) for provider in providers]
        stats.sort(key=lambda item: item.get("avg_reputation", 0.0), reverse=True)
        return {"providers": stats[:limit]}

    @staticmethod
    def _external_resource_hub(args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).lower()
        limit = int(args.get("limit", 5))
        resources = [
            {
                "title": "Model Context Protocol - Architecture",
                "url": "https://modelcontextprotocol.io/specification/2025-06-18/architecture/index",
                "tags": ["mcp", "tooling", "protocol", "security"],
            },
            {
                "title": "LangGraph Overview",
                "url": "https://docs.langchain.com/oss/python/langgraph/overview",
                "tags": ["langgraph", "state", "durability", "agent"],
            },
            {
                "title": "GitHub Trending Weekly",
                "url": "https://github.com/trending?since=weekly",
                "tags": ["github", "trending", "hotspot", "ecosystem"],
            },
            {
                "title": "OpenAI Building Agents Guide",
                "url": "https://developers.openai.com/resources/",
                "tags": ["openai", "agents", "evals", "safety"],
            },
        ]

        scored: list[tuple[dict[str, Any], float]] = []
        for item in resources:
            score = 0.2
            for tag in item["tags"]:
                if tag in query:
                    score += 0.25
            scored.append((item, score))
        scored.sort(key=lambda pair: pair[1], reverse=True)

        return {
            "resources": [
                {"title": item["title"], "url": item["url"], "score": round(score, 3), "tags": item["tags"]}
                for item, score in scored[:limit]
            ]
        }

    @staticmethod
    def _api_skill_dependency_graph(args: dict[str, Any]) -> dict[str, Any]:
        limit = int(args.get("limit", 20))
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        all_skills = list_all_skills()
        for meta in all_skills:
            nodes.append(
                {
                    "id": meta.name,
                    "category": meta.category.value,
                    "tier": meta.tier.value,
                    "cost": meta.compute_cost,
                }
            )
            for target in meta.synergies:
                edges.append({"from": meta.name, "to": target, "type": "synergy"})
            for target in meta.conflicts:
                edges.append({"from": meta.name, "to": target, "type": "conflict"})

        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes[:limit],
            "edges": edges[:limit],
        }

    @staticmethod
    def _code_router_blueprint(args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", ""))
        return {
            "query": query,
            "blueprint": [
                {
                    "phase": "observe",
                    "objective": "Capture routing, guardrail, and tool telemetry as first-class trace.",
                    "artifacts": ["discovery_trace", "security_decisions", "step_latency"],
                },
                {
                    "phase": "decide",
                    "objective": "Apply policy-conditioned tool selection with explicit rationale.",
                    "artifacts": ["tool_manifest", "recipe_decision", "fallback_chain"],
                },
                {
                    "phase": "adapt",
                    "objective": "Continuously improve selection from eval and red-team outcomes.",
                    "artifacts": ["eval_metrics", "redteam_pass_rate", "failure_clusters"],
                },
            ],
            "design_principles": [
                "Prefer composable tool cards over hard-coded orchestration.",
                "Treat security checks as executable policy, not static docs.",
                "Keep each loop step explainable with source + score + constraints.",
            ],
        }
