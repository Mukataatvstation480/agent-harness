"""Harness planner and dynamic tool scheduling."""

from __future__ import annotations

from typing import Any

from app.harness.models import ToolCall, ToolType
from app.harness.task_profile import TaskProfile, analyze_task_request


class HarnessPlanner:
    """Generate task-aware plans and fallback tool decisions."""

    def build_plan(
        self,
        query: str,
        *,
        target: str = "general",
        live_model_overrides: dict[str, Any] | None = None,
    ) -> list[str]:
        """Build a lightweight plan from capability-graph planning."""

        profile = analyze_task_request(query, target=target, live_model_overrides=live_model_overrides)
        task_spec = profile.task_spec if isinstance(profile.task_spec, dict) else {}
        primary_artifact = str(task_spec.get("primary_artifact_kind", profile.output_mode)).strip()
        plan = ["understand goal, constraints, and desired end state"]
        steps = profile.capability_plan.get("steps", []) if isinstance(profile.capability_plan.get("steps", []), list) else []
        for step in steps[:8]:
            if not isinstance(step, dict):
                continue
            title = str(step.get("title", "")).strip()
            reason = str(step.get("reason", "")).strip()
            if title:
                plan.append(f"{title.lower()} because {reason or 'the capability graph selected it'}")
        if profile.requires_validation:
            plan.append("validate the result against the task success criteria and remaining state gap")
        if profile.requires_command_execution:
            plan.append("execute bounded workspace commands only if they reduce the remaining state gap")
        plan.append(f"close the remaining artifact gap and publish the primary deliverable: {primary_artifact or profile.output_mode}")
        return plan

    def next_tool_call(
        self,
        query: str,
        step: int,
        plan: list[str],
        *,
        target: str = "general",
        session_events: list[dict[str, object]] | None = None,
        used_tools: set[str] | None = None,
        live_model_overrides: dict[str, Any] | None = None,
    ) -> ToolCall | None:
        """Choose the next fallback tool from missing signals, not fixed steps."""

        del step, plan  # planner is state-driven rather than step-template-driven

        profile = analyze_task_request(query, target=target, live_model_overrides=live_model_overrides)
        used = {str(item).strip() for item in (used_tools or set()) if str(item).strip()}
        events = session_events or []
        event_tools = {
            str(item.get("tool", "")).strip()
            for item in events
            if isinstance(item, dict) and str(item.get("tool", "")).strip()
        }
        seen = used | event_tools

        for tool_name, args in self._candidate_tool_sequence(profile):
            if tool_name in seen:
                continue
            return ToolCall(
                name=tool_name,
                tool_type=self._tool_type(tool_name),
                args=args,
            )
        return None

    @staticmethod
    def _candidate_tool_sequence(profile: TaskProfile) -> list[tuple[str, dict[str, object]]]:
        task_spec = profile.task_spec if isinstance(profile.task_spec, dict) else {}
        required_channels = {
            str(item).strip()
            for item in task_spec.get("required_channels", [])
            if str(item).strip()
        }
        primary_artifact = str(task_spec.get("primary_artifact_kind", "")).strip()
        keywords = profile.keywords or [primary_artifact or profile.execution_intent or "task"]
        primary = keywords[0] if keywords else profile.query
        skill_query = " ".join(
            item
            for item in [primary_artifact, " ".join(sorted(required_channels)), " ".join(keywords[:2])]
            if str(item).strip()
        ).strip() or profile.query
        glob = HarnessPlanner._workspace_glob(profile=profile, primary_artifact=primary_artifact)

        sequence: list[tuple[str, dict[str, object]]] = []
        seen_tools: set[str] = set()
        for step in profile.capability_plan.get("steps", []) if isinstance(profile.capability_plan.get("steps", []), list) else []:
            if not isinstance(step, dict) or str(step.get("node_type", "")) != "tool_call":
                continue
            ref = str(step.get("ref", "")).strip()
            if not ref:
                continue
            seen_tools.add(ref)
            args = dict(step.get("default_args", {})) if isinstance(step.get("default_args", {}), dict) else {}
            if ref == "workspace_file_search":
                args.setdefault("query", primary)
                args.setdefault("glob", glob)
                args.setdefault("limit", 8)
            elif ref == "code_skill_search":
                args.setdefault("query", skill_query)
                args.setdefault("limit", 6)
            elif ref == "external_resource_hub":
                args.setdefault("query", profile.query)
                args.setdefault("limit", 6)
            elif ref == "evidence_dossier_builder":
                args.setdefault("query", profile.query)
                args.setdefault("limit", 5)
                args.setdefault("domains", profile.domains or ["general"])
            elif ref == "policy_risk_matrix":
                args.setdefault("query", profile.query)
                args.setdefault("evidence_limit", 4)
            else:
                args.setdefault("query", profile.query)
            sequence.append((ref, args))

        for tool_name, args in HarnessPlanner._channel_fallback_tools(
            profile=profile,
            required_channels=required_channels,
            primary_artifact=primary_artifact,
            primary=primary,
            skill_query=skill_query,
            glob=glob,
            seen_tools=seen_tools,
        ):
            seen_tools.add(tool_name)
            sequence.append((tool_name, args))

        if profile.requires_validation and "workspace" in required_channels:
            sequence.append(("memory_context_digest", {"events": []}))
        return sequence

    @staticmethod
    def _channel_fallback_tools(
        *,
        profile: TaskProfile,
        required_channels: set[str],
        primary_artifact: str,
        primary: str,
        skill_query: str,
        glob: str,
        seen_tools: set[str],
    ) -> list[tuple[str, dict[str, object]]]:
        sequence: list[tuple[str, dict[str, object]]] = []
        if "discovery" in required_channels and "tool_search" not in seen_tools:
            sequence.append(("tool_search", {"query": primary_artifact or profile.query, "limit": 6}))
        if "discovery" in required_channels and "code_skill_search" not in seen_tools:
            sequence.append(("code_skill_search", {"query": skill_query, "target": profile.target_hint, "limit": 6}))
        if "workspace" in required_channels and "workspace_file_search" not in seen_tools:
            sequence.append(("workspace_file_search", {"query": primary, "glob": glob, "limit": 8}))
        if "web" in required_channels and "external_resource_hub" not in seen_tools:
            sequence.append(("external_resource_hub", {"query": profile.query, "limit": 6}))
        if (
            "web" in required_channels
            and primary_artifact in {"deliverable_report", "data_analysis_spec"}
            and "evidence_dossier_builder" not in seen_tools
        ):
            sequence.append(
                ("evidence_dossier_builder", {"query": profile.query, "limit": 5, "domains": profile.domains or ["general"]})
            )
        if "risk" in required_channels and "policy_risk_matrix" not in seen_tools:
            sequence.append(("policy_risk_matrix", {"query": profile.query, "evidence_limit": 4}))
        return sequence

    @staticmethod
    def _workspace_glob(*, profile: TaskProfile, primary_artifact: str) -> str:
        languages = {
            str(item).strip().lower()
            for item in profile.workspace_summary.get("languages", [])
            if str(item).strip()
        } if isinstance(profile.workspace_summary, dict) else set()
        if primary_artifact in {"patch_draft", "patch_plan"}:
            if "python" in languages:
                return "*.py"
            if {"typescript", "javascript"} & languages:
                return "*.{ts,tsx,js,jsx}"
            return "*"
        return "*"

    @staticmethod
    def _tool_type(tool_name: str) -> ToolType:
        mapping = {
            "workspace_file_search": ToolType.CODE,
            "external_resource_hub": ToolType.BROWSER,
            "evidence_dossier_builder": ToolType.BROWSER,
            "tool_search": ToolType.CODE,
            "code_skill_search": ToolType.CODE,
            "policy_risk_matrix": ToolType.CODE,
            "code_experiment_design": ToolType.CODE,
            "memory_context_digest": ToolType.CODE,
        }
        return mapping.get(tool_name, ToolType.CODE)
