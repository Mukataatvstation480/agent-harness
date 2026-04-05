"""Dynamic task understanding, channel deliberation, and graph compilation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.tasking import allowed_workspace_action_kinds, default_capability_registry, infer_task_spec, plan_capability_path
from app.core.state import SkillCategory
from app.core.task_graph import ExecutableTaskGraph, TaskGraphNode
from app.skills.packages import SkillPackageCatalog
from app.skills.registry import list_all_skills


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{1,}|[\u4e00-\u9fff]{2,}")


def _tokens(text: str) -> list[str]:
    raw_tokens = [token.lower() for token in _TOKEN_RE.findall(str(text or ""))]
    expanded: list[str] = []
    for token in raw_tokens:
        if token not in expanded:
            expanded.append(token)
        if "-" in token or "_" in token:
            for part in re.split(r"[-_]+", token):
                normalized = part.strip().lower()
                if len(normalized) >= 2 and normalized not in expanded:
                    expanded.append(normalized)
    return expanded


def _count_markers(lowered: str, markers: list[str]) -> int:
    tokens = set(_tokens(lowered))
    total = 0
    for marker in markers:
        marker_text = str(marker or "").lower()
        if not marker_text:
            continue
        if re.fullmatch(r"[a-z0-9_-]+", marker_text):
            if marker_text in tokens:
                total += 1
            continue
        if marker_text in lowered:
            total += 1
    return total


def _slugify(parts: list[str], fallback: str = "task") -> str:
    text = "-".join(part.strip().lower() for part in parts if part.strip()) or fallback
    text = re.sub(r"[^a-z0-9_-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or fallback


@dataclass(frozen=True)
class SkillPrior:
    """A ranked skill prior used to bias planning without fixing the workflow."""

    name: str
    score: float
    rationale: list[str] = field(default_factory=list)
    category: str = ""
    tier: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "score": round(self.score, 4),
            "rationale": list(self.rationale),
            "category": self.category,
            "tier": self.tier,
        }


@dataclass(frozen=True)
class ChannelDeliberation:
    """Agent-style evidence-channel selection result."""

    scores: dict[str, float] = field(default_factory=dict)
    selected: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "scores": {key: round(value, 4) for key, value in self.scores.items()},
            "selected": list(self.selected),
            "rationale": list(self.rationale),
        }


@dataclass(frozen=True)
class TaskProfile:
    """Shared task profile for planner, graph compiler, and runtime surfaces."""

    query: str
    target_hint: str
    evidence_strategy: str
    execution_intent: str
    output_mode: str
    reasoning_style: str
    domains: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    requires_workspace: bool = False
    requires_external_evidence: bool = False
    requires_discovery: bool = True
    requires_validation: bool = False
    requires_command_execution: bool = False
    artifact_targets: list[str] = field(default_factory=list)
    workspace_summary: dict[str, Any] = field(default_factory=dict)
    task_spec: dict[str, Any] = field(default_factory=dict)
    capability_plan: dict[str, Any] = field(default_factory=dict)
    execution_loop: dict[str, Any] = field(default_factory=dict)
    graph_expansion: dict[str, Any] = field(default_factory=dict)
    skill_priors: list[SkillPrior] = field(default_factory=list)
    package_priors: list[dict[str, Any]] = field(default_factory=list)
    deliberation: ChannelDeliberation = field(default_factory=ChannelDeliberation)

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "target_hint": self.target_hint,
            "evidence_strategy": self.evidence_strategy,
            "execution_intent": self.execution_intent,
            "output_mode": self.output_mode,
            "reasoning_style": self.reasoning_style,
            "domains": list(self.domains),
            "keywords": list(self.keywords),
            "requires_workspace": self.requires_workspace,
            "requires_external_evidence": self.requires_external_evidence,
            "requires_discovery": self.requires_discovery,
            "requires_validation": self.requires_validation,
            "requires_command_execution": self.requires_command_execution,
            "artifact_targets": list(self.artifact_targets),
            "workspace_summary": dict(self.workspace_summary),
            "task_spec": dict(self.task_spec),
            "capability_plan": dict(self.capability_plan),
            "execution_loop": dict(self.execution_loop),
            "graph_expansion": dict(self.graph_expansion),
            "skill_priors": [item.to_dict() for item in self.skill_priors],
            "package_priors": [dict(item) for item in self.package_priors],
            "deliberation": self.deliberation.to_dict(),
            "selected_channels": list(self.deliberation.selected),
        }


def infer_domains(query: str) -> list[str]:
    """Infer topical domains from free-form task text."""

    lowered = str(query or "").lower()
    mapping = {
        "risk": [
            "risk",
            "security",
            "audit",
            "compliance",
            "governance",
            "control",
            "\u98ce\u63a7",
            "\u5b89\u5168",
            "\u5ba1\u8ba1",
            "\u5408\u89c4",
            "\u6cbb\u7406",
        ],
        "enterprise": [
            "enterprise",
            "workflow",
            "operations",
            "stakeholder",
            "board",
            "ops",
            "\u4f01\u4e1a",
            "\u6d41\u7a0b",
            "\u8fd0\u8425",
        ],
        "research": [
            "research",
            "experiment",
            "study",
            "evaluation",
            "paper",
            "\u7814\u7a76",
            "\u8bc4\u6d4b",
            "\u8bba\u6587",
            "\u5b9e\u9a8c",
        ],
        "fintech": [
            "fintech",
            "bank",
            "payments",
            "insurance",
            "customer support",
            "\u91d1\u878d",
            "\u94f6\u884c",
            "\u652f\u4ed8",
            "\u4fdd\u9669",
        ],
        "engineering": [
            "code",
            "repo",
            "repository",
            "workspace",
            "module",
            "patch",
            "test",
            "bug",
            "implementation",
            "architecture",
            "migration",
            "validate",
            "validation",
            "\u4ee3\u7801",
            "\u4ed3\u5e93",
            "\u6a21\u5757",
            "\u8865\u4e01",
            "\u6d4b\u8bd5",
            "\u7f3a\u9677",
            "\u5b9e\u73b0",
            "\u67b6\u6784",
            "\u8fc1\u79fb",
            "\u9a8c\u8bc1",
        ],
    }
    domains = [domain for domain, markers in mapping.items() if any(marker in lowered for marker in markers)]
    return domains or ["general"]


def analyze_task_request(
    query: str,
    *,
    target: str = "general",
    workspace_root: str | Path | None = None,
    skill_limit: int = 4,
    live_model_overrides: dict[str, Any] | None = None,
) -> TaskProfile:
    """Infer a reusable task profile from a free-form request."""

    lowered = str(query or "").strip().lower()
    keywords = list(dict.fromkeys(_tokens(query)))[:8]
    target_hint = str(target or "general").strip().lower() or "general"
    package_catalog = SkillPackageCatalog()
    package_priors = []
    for item in package_catalog.suggest(query, target=target_hint, limit=max(4, skill_limit)):
        payload = item.to_dict()
        payload["match_score"] = round(item.score_for_query(query, target=target_hint), 4)
        package_priors.append(payload)
    package_channels = _required_channels_from_packages(package_priors)
    package_validation = any("validation" in [str(req).strip().lower() for req in item.get("runtime_requirements", [])] for item in package_priors)

    workspace_markers = [
        "repo",
        "repository",
        "workspace",
        "file",
        "module",
        "code",
        "bug",
        "patch",
        "test",
        "refactor",
        "my repo",
        "this repo",
        "my repository",
        "\u4ed3\u5e93",
        "\u4ee3\u7801",
        "\u6587\u4ef6",
        "\u6a21\u5757",
        "\u8865\u4e01",
        "\u6d4b\u8bd5",
        "\u4fee\u590d",
    ]
    external_markers = [
        "research",
        "report",
        "topic",
        "evidence",
        "external",
        "source",
        "citation",
        "market",
        "trend",
        "state of the art",
        "paper",
        "compare",
        "internet",
        "web",
        "latest",
        "\u7814\u7a76",
        "\u62a5\u544a",
        "\u8d8b\u52bf",
        "\u8bba\u6587",
        "\u5bf9\u6bd4",
        "\u7f51\u4e0a",
        "\u8c03\u7814",
    ]
    code_markers = [
        "patch",
        "test",
        "tests",
        "bug",
        "refactor",
        "fix",
        "fixes",
        "implement",
        "validation",
        "execute",
        "run",
        "build",
        "\u4ee3\u7801",
        "\u8865\u4e01",
        "\u6d4b\u8bd5",
        "\u4fee\u590d",
        "\u5b9e\u73b0",
        "\u8fd0\u884c",
        "\u6784\u5efa",
    ]
    ops_markers = [
        "runbook",
        "incident",
        "ops",
        "workflow",
        "playbook",
        "governance",
        "policy",
        "escalation",
        "\u8fd0\u7ef4",
        "\u6d41\u7a0b",
        "\u6cbb\u7406",
        "\u7b56\u7565",
    ]
    workspace_signal = _count_markers(lowered, workspace_markers)
    external_signal = _count_markers(lowered, external_markers)
    code_signal = _count_markers(lowered, code_markers)
    ops_signal = _count_markers(lowered, ops_markers)

    if target_hint == "code":
        workspace_signal += 2
        code_signal += 2
    elif target_hint == "research":
        external_signal += 2
    elif target_hint == "ops":
        ops_signal += 2

    workspace_summary = inspect_workspace_capabilities(workspace_root)
    requested_modes = requested_output_modes(query=query, output_mode="artifact")
    provisional_output_mode = requested_modes[0] if requested_modes else "artifact"
    validation_markers = [
        "validate",
        "validation",
        "test",
        "tests",
        "check",
        "verify",
        "acceptance",
        "\u6d4b\u8bd5",
        "\u9a8c\u8bc1",
        "\u6267\u884c",
    ]
    provisional_command_execution = (
        bool(workspace_summary.get("suggested_commands", []))
        and (workspace_signal > 0 or target_hint == "code")
        and any(marker in lowered for marker in ["run", "execute", "build", "test", "validation", "\u8fd0\u884c", "\u6267\u884c", "\u6d4b\u8bd5"])
    )
    provisional_validation = (
        package_validation
        or provisional_command_execution
        or any(mode in {"patch", "chart", "data"} for mode in requested_modes)
        or any(marker in lowered for marker in validation_markers)
    )
    task_spec = infer_task_spec(
        query=query,
        target=target_hint,
        domains=infer_domains(query),
        output_mode=provisional_output_mode,
        workspace_required=workspace_signal > 0 or "workspace" in package_channels,
        external_required=external_signal > 0 or "web" in package_channels,
        needs_validation=provisional_validation,
        needs_command_execution=provisional_command_execution,
    )
    capability_plan = plan_capability_path(
        task_spec=task_spec,
        registry=default_capability_registry(),
    )
    output_mode = _derive_output_mode_from_task_spec(task_spec.to_dict())
    execution_intent = _derive_execution_intent(
        task_spec=task_spec.to_dict(),
        target_hint=target_hint,
        workspace_summary=workspace_summary,
    )
    reasoning_style = _derive_reasoning_style(
        task_spec=task_spec.to_dict(),
        execution_intent=execution_intent,
        output_mode=output_mode,
    )
    provisional_execution_loop = build_execution_loop(
        query=query,
        task_spec=task_spec.to_dict(),
        selected_channels=list(dict.fromkeys(task_spec.required_channels + capability_plan.get("required_channels", []))),
        capability_plan=capability_plan,
        graph_expansion={},
        requires_command_execution=provisional_command_execution,
    )
    skill_priors = select_skill_priors(
        query=query,
        task_spec=task_spec.to_dict(),
        capability_plan=capability_plan,
        execution_loop=provisional_execution_loop,
        package_priors=package_priors,
        limit=skill_limit,
    )
    local_deliberation = deliberate_channels(
        query=query,
        target=target_hint,
        execution_intent=execution_intent,
        output_mode=output_mode,
        task_spec=task_spec.to_dict(),
        capability_plan=capability_plan,
        skill_priors=skill_priors,
        workspace_root=workspace_root,
        workspace_signal=workspace_signal,
        external_signal=external_signal,
        code_signal=code_signal,
        ops_signal=ops_signal,
    )
    provisional_execution_loop = build_execution_loop(
        query=query,
        task_spec=task_spec.to_dict(),
        selected_channels=local_deliberation.selected,
        capability_plan=capability_plan,
        graph_expansion={},
        requires_command_execution=provisional_command_execution,
    )
    deliberation = refine_deliberation_with_live_model(
        query=query,
        target=target_hint,
        execution_intent=execution_intent,
        output_mode=output_mode,
        skill_priors=skill_priors,
        workspace_summary=workspace_summary,
        execution_loop=provisional_execution_loop,
        required_channels=list(dict.fromkeys(task_spec.required_channels + capability_plan.get("required_channels", []))),
        local=local_deliberation,
        live_model_overrides=live_model_overrides,
    )
    merged_selected = list(dict.fromkeys(list(deliberation.selected) + list(capability_plan.get("required_channels", []))))
    merged_selected = list(dict.fromkeys(merged_selected + package_channels))
    if (
        workspace_signal <= 0
        and target_hint == "research"
        and external_signal > 0
        and "web" in merged_selected
        and "workspace" in merged_selected
        and "workspace" not in task_spec.required_channels
    ):
        merged_selected = [item for item in merged_selected if item != "workspace"]
    deliberation = ChannelDeliberation(
        scores=dict(deliberation.scores),
        selected=merged_selected,
        rationale=list(deliberation.rationale)
        + (["capability graph requested additional channels"] if merged_selected != deliberation.selected else [])
        + (["skill packages requested additional channels"] if any(channel not in deliberation.selected for channel in package_channels) else []),
    )

    selected = set(deliberation.selected)
    requires_workspace = "workspace" in selected
    requires_external_evidence = "web" in selected
    requires_discovery = "discovery" in selected or not selected
    requires_validation = provisional_validation
    requires_command_execution = provisional_command_execution

    if requires_workspace and requires_external_evidence:
        evidence_strategy = "hybrid"
    elif requires_workspace:
        evidence_strategy = "workspace"
    elif requires_external_evidence:
        evidence_strategy = "web"
    else:
        evidence_strategy = "minimal"

    graph_expansion = plan_graph_expansion(
        query=query,
        execution_intent=execution_intent,
        output_mode=output_mode,
        selected_channels=deliberation.selected,
        workspace_summary=workspace_summary,
        requires_command_execution=requires_command_execution,
        live_model_overrides=live_model_overrides,
        skill_priors=skill_priors,
        package_priors=package_priors,
        task_spec=task_spec.to_dict(),
        capability_plan=capability_plan,
    )
    execution_loop = build_execution_loop(
        query=query,
        task_spec=task_spec.to_dict(),
        selected_channels=deliberation.selected,
        capability_plan=capability_plan,
        graph_expansion=graph_expansion,
        requires_command_execution=requires_command_execution,
    )

    return TaskProfile(
        query=query,
        target_hint=target_hint,
        evidence_strategy=evidence_strategy,
        execution_intent=execution_intent,
        output_mode=output_mode,
        reasoning_style=reasoning_style,
        domains=infer_domains(query),
        keywords=keywords,
        requires_workspace=requires_workspace,
        requires_external_evidence=requires_external_evidence,
        requires_discovery=requires_discovery,
        requires_validation=requires_validation,
        requires_command_execution=requires_command_execution,
        artifact_targets=default_artifact_targets(
            query=query,
            selected_channels=deliberation.selected,
            output_mode=output_mode,
            requires_validation=requires_validation,
            requires_command_execution=requires_command_execution,
        ),
        workspace_summary=workspace_summary,
        task_spec=task_spec.to_dict(),
        capability_plan=capability_plan,
        execution_loop=execution_loop,
        graph_expansion=graph_expansion,
        skill_priors=skill_priors,
        package_priors=package_priors,
        deliberation=deliberation,
    )


def build_execution_loop(
    *,
    query: str,
    task_spec: dict[str, Any],
    selected_channels: list[str],
    capability_plan: dict[str, Any],
    graph_expansion: dict[str, Any],
    requires_command_execution: bool,
) -> dict[str, Any]:
    """Build a simple thread-visible execution loop summary."""

    contracts = task_spec.get("artifact_contracts", []) if isinstance(task_spec.get("artifact_contracts", []), list) else []
    primary_artifact = str(task_spec.get("primary_artifact_kind", "")).strip() or "deliverable_report"
    observe_focus: list[str] = []
    for channel, label in [
        ("discovery", "discover available tools and skills"),
        ("workspace", "inspect local workspace state"),
        ("web", "collect external evidence"),
        ("risk", "evaluate risk and governance constraints"),
    ]:
        if channel in selected_channels:
            observe_focus.append(label)
    act_focus = [
        str(item.get("title", item.get("kind", ""))).strip()
        for item in graph_expansion.get("actions", [])
        if isinstance(item, dict) and str(item.get("title", item.get("kind", ""))).strip()
    ][:4]
    if requires_command_execution:
        act_focus.append("run targeted workspace execution")
    deliverables = [
        str(item.get("title", item.get("kind", ""))).strip()
        for item in contracts
        if isinstance(item, dict) and str(item.get("kind", "")) not in {"completion_packet", "delivery_bundle"}
    ]
    phases = [
        {
            "phase": "observe",
            "goal": "reduce uncertainty before committing to an execution path",
            "focus": observe_focus or ["capture only the minimum context needed to act"],
        },
        {
            "phase": "decide",
            "goal": "turn the request into a bounded execution plan",
            "focus": [
                "analyze the task against requested deliverables",
                "pick the smallest capability path that can close the task",
            ],
        },
        {
            "phase": "act",
            "goal": "materialize the requested work instead of stopping at diagnosis",
            "focus": act_focus or ["execute the smallest artifact-producing action that moves the task forward"],
        },
        {
            "phase": "deliver",
            "goal": "ship a reviewer-first primary artifact with closure context",
            "focus": deliverables[:4] or [primary_artifact.replace("_", " ")],
        },
    ]
    return {
        "schema": "agent-harness-generic-loop/v1",
        "query": query,
        "primary_artifact_kind": primary_artifact,
        "selected_channels": list(selected_channels),
        "deliverables": deliverables[:6],
        "capability_count": len(capability_plan.get("steps", [])) if isinstance(capability_plan.get("steps", []), list) else 0,
        "expansion_count": len(graph_expansion.get("actions", [])) if isinstance(graph_expansion.get("actions", []), list) else 0,
        "phases": phases,
    }


def _material_contract_kinds(task_spec: dict[str, Any]) -> list[str]:
    support_kinds = {"completion_packet", "delivery_bundle"}
    contracts = task_spec.get("artifact_contracts", []) if isinstance(task_spec.get("artifact_contracts", []), list) else []
    kinds: list[str] = []
    for item in contracts:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", "")).strip()
        if not kind or kind in support_kinds or kind in kinds:
            continue
        kinds.append(kind)
    return kinds


def _surface_mode_for_artifact(kind: str) -> str:
    normalized = str(kind or "").strip()
    if normalized in {"patch_plan", "patch_draft"}:
        return "patch"
    if normalized in {"runbook", "custom:checklist"}:
        return "runbook"
    if normalized == "webpage_blueprint":
        return "webpage"
    if normalized == "slide_deck_plan":
        return "slides"
    if normalized == "chart_pack_spec":
        return "chart"
    if normalized == "podcast_episode_plan":
        return "podcast"
    if normalized == "video_storyboard":
        return "video"
    if normalized == "image_prompt_pack":
        return "image"
    if normalized in {"data_analysis_spec", "dataset_pull_spec", "dataset_loader_template"}:
        return "data"
    if _is_report_like_artifact(normalized):
        return "report"
    return "artifact"


def output_modes_from_task_spec(task_spec: dict[str, Any]) -> list[str]:
    """Derive requested output surfaces from artifact contracts instead of query templates."""

    modes: list[str] = []
    for kind in _material_contract_kinds(task_spec):
        mode = _surface_mode_for_artifact(kind)
        if mode not in modes:
            modes.append(mode)
    return modes or ["artifact"]


def _derive_output_mode_from_task_spec(task_spec: dict[str, Any]) -> str:
    primary = str(task_spec.get("primary_artifact_kind", "")).strip()
    if primary:
        return _surface_mode_for_artifact(primary)
    return output_modes_from_task_spec(task_spec)[0]


def _derive_execution_intent(
    *,
    task_spec: dict[str, Any],
    target_hint: str,
    workspace_summary: dict[str, Any],
) -> str:
    """Project a stable execution intent from task structure, not keyword classes."""

    channels = set(
        str(item).strip()
        for item in task_spec.get("required_channels", [])
        if str(item).strip()
    ) if isinstance(task_spec.get("required_channels", []), list) else set()
    material_contracts = _material_contract_kinds(task_spec)
    primary = str(task_spec.get("primary_artifact_kind", "")).strip()
    has_workspace_contract = any(_surface_mode_for_artifact(item) == "patch" for item in material_contracts)
    has_ops_contract = any(item in {"runbook", "custom:checklist", "risk_register"} for item in material_contracts)
    has_report_contract = any(_surface_mode_for_artifact(item) == "report" for item in material_contracts)
    has_visual_contract = any(
        _surface_mode_for_artifact(item) in {"webpage", "slides", "chart", "podcast", "video", "image", "data"}
        for item in material_contracts
    )
    needs_validation = bool(task_spec.get("needs_validation", False))
    command_ready = bool(workspace_summary.get("suggested_commands", [])) and bool(task_spec.get("needs_command_execution", False))

    if has_workspace_contract or command_ready or ("workspace" in channels and needs_validation):
        return "code"
    if "workspace" in channels and "web" in channels:
        return "mixed"
    if has_ops_contract or ("risk" in channels and primary != "deliverable_report"):
        return "ops"
    if "web" in channels and "workspace" not in channels and (has_report_contract or not has_visual_contract or target_hint == "research"):
        return "research"
    if target_hint == "code" and "workspace" in channels:
        return "code"
    if target_hint == "ops" and ("risk" in channels or has_ops_contract):
        return "ops"
    if target_hint == "research" and "web" in channels and "workspace" not in channels:
        return "research"
    return "general"


def _derive_reasoning_style(*, task_spec: dict[str, Any], execution_intent: str, output_mode: str) -> str:
    channels = set(
        str(item).strip()
        for item in task_spec.get("required_channels", [])
        if str(item).strip()
    ) if isinstance(task_spec.get("required_channels", []), list) else set()
    if execution_intent == "code":
        return "debug"
    if execution_intent == "ops":
        return "procedural"
    if execution_intent == "research" or ("web" in channels and output_mode == "report"):
        return "evidence-led"
    if output_mode in {"webpage", "slides", "podcast", "video", "image"}:
        return "creative"
    if output_mode in {"chart", "data"}:
        return "analytic"
    return "deliberate"


def select_skill_priors(
    query: str,
    *,
    task_spec: dict[str, Any] | None = None,
    capability_plan: dict[str, Any] | None = None,
    execution_loop: dict[str, Any] | None = None,
    package_priors: list[dict[str, Any]] | None = None,
    limit: int = 4,
) -> list[SkillPrior]:
    """Select skill priors from task contracts/capabilities instead of query heuristics."""

    del query
    task_spec = task_spec or {}
    capability_plan = capability_plan or {}
    execution_loop = execution_loop or {}

    skill_meta = {meta.name: meta for meta in list_all_skills()}
    scores: dict[str, float] = {}
    rationales: dict[str, list[str]] = {}

    def add(name: str, score: float, reason: str) -> None:
        meta = skill_meta.get(name)
        if meta is None:
            return
        scores[name] = scores.get(name, 0.0) + score
        rationales.setdefault(name, [])
        if reason not in rationales[name]:
            rationales[name].append(reason)

    channels = [
        str(item).strip()
        for item in task_spec.get("required_channels", [])
        if str(item).strip()
    ] if isinstance(task_spec.get("required_channels", []), list) else []
    material_contracts = _material_contract_kinds(task_spec)
    output_modes = output_modes_from_task_spec(task_spec)
    capability_steps = capability_plan.get("steps", []) if isinstance(capability_plan.get("steps", []), list) else []

    for channel in channels:
        if channel == "discovery":
            add("decompose_task", 0.5, "task spec requires discovery-first decomposition")
        elif channel == "workspace":
            add("codebase_triage", 0.42, "workspace channel requires local artifact inspection")
        elif channel == "web":
            add("extract_facts", 0.34, "web channel requires evidence extraction")
            add("validate_claims", 0.26, "web channel benefits from explicit claim checking")
        elif channel == "risk":
            add("identify_risks", 0.34, "risk channel requires governance/risk inspection")
            add("ops_runbook", 0.16, "risk channel benefits from operational closure guidance")

    for step in capability_steps:
        if not isinstance(step, dict):
            continue
        ref = str(step.get("ref", "")).strip()
        capability = str(step.get("capability", "")).strip()
        reason = str(step.get("reason", "")).strip() or capability or ref
        if ref in skill_meta:
            add(ref, 0.46, f"capability plan includes {reason}")
        if capability == "plan_validation":
            add("validation_planner", 0.42, "capability graph leaves an explicit validation step")
        if capability == "decompose_task":
            add("decompose_task", 0.44, "capability graph includes task decomposition")

    contract_skill_support = {
        "patch_plan": [("codebase_triage", 0.54), ("validation_planner", 0.28)],
        "patch_draft": [("codebase_triage", 0.56), ("validation_planner", 0.32)],
        "runbook": [("ops_runbook", 0.58), ("identify_risks", 0.28)],
        "risk_register": [("identify_risks", 0.5), ("ops_runbook", 0.24)],
        "custom:checklist": [("ops_runbook", 0.42), ("prioritize_items", 0.18)],
        "webpage_blueprint": [("webpage_blueprint", 0.58), ("frontend_critique", 0.26)],
        "slide_deck_plan": [("slide_deck_designer", 0.58), ("executive_summary", 0.18)],
        "chart_pack_spec": [("chart_storyboard", 0.58), ("data_analysis_plan", 0.28)],
        "podcast_episode_plan": [("podcast_episode_plan", 0.58), ("synthesize_perspectives", 0.18)],
        "video_storyboard": [("video_storyboard", 0.58), ("image_prompt_pack", 0.18)],
        "image_prompt_pack": [("image_prompt_pack", 0.58), ("brainstorm_ideas", 0.18)],
        "data_analysis_spec": [("data_analysis_plan", 0.58), ("chart_storyboard", 0.22)],
        "dataset_pull_spec": [("data_analysis_plan", 0.44), ("extract_facts", 0.2)],
        "dataset_loader_template": [("data_analysis_plan", 0.42), ("validation_planner", 0.18)],
        "deliverable_report": [("artifact_synthesis", 0.42), ("executive_summary", 0.16)],
        "evidence_bundle": [("research_brief", 0.24), ("extract_facts", 0.28)],
        "workspace_findings": [("codebase_triage", 0.22), ("artifact_synthesis", 0.16)],
    }
    for kind in material_contracts:
        if kind.startswith("custom:") and kind != "custom:checklist":
            add("artifact_synthesis", 0.48, f"{kind} is a structured document contract")
            add("executive_summary", 0.18, f"{kind} benefits from concise framing")
            continue
        for skill_name, score in contract_skill_support.get(kind, []):
            add(skill_name, score, f"artifact contract requires {kind}")

    if len(material_contracts) > 1 or len(output_modes) > 1:
        add("artifact_synthesis", 0.44, "multiple deliverables need one coherent synthesis layer")

    if bool(task_spec.get("needs_validation", False)):
        add("validation_planner", 0.38, "task spec explicitly requires validation closure")

    deliver_focus = execution_loop.get("deliverables", []) if isinstance(execution_loop.get("deliverables", []), list) else []
    if deliver_focus:
        primary_skill = _select_synthesis_skill(
            query="",
            primary_artifact_kind=str(task_spec.get("primary_artifact_kind", "")).strip(),
            selected_channels=set(channels),
            research_surface="web" in channels and "workspace" not in channels,
            contracts=task_spec.get("artifact_contracts", []) if isinstance(task_spec.get("artifact_contracts", []), list) else [],
            requested_surface_count=len(output_modes),
        )
        add(primary_skill, 0.36, "execution loop needs a primary delivery skill")

    for package in package_priors or []:
        if not isinstance(package, dict):
            continue
        if float(package.get("match_score", 0.0) or 0.0) < 0.42:
            continue
        package_name = str(package.get("name", "")).strip() or "package"
        for skill_name in package.get("skill_refs", []) if isinstance(package.get("skill_refs", []), list) else []:
            skill_text = str(skill_name).strip()
            if skill_text:
                add(skill_text, 0.34, f"package prior recommends {package_name}")

    if not scores:
        fallback = ["decompose_task", "artifact_synthesis", "executive_summary"]
        return [
            SkillPrior(name=name, score=0.25 - 0.02 * index, rationale=["structural fallback"])
            for index, name in enumerate(fallback[:limit])
        ]

    priors = [
        SkillPrior(
            name=name,
            score=score + (0.03 if skill_meta[name].category in {SkillCategory.ANALYSIS, SkillCategory.REASONING} else 0.0),
            rationale=rationales.get(name, []),
            category=skill_meta[name].category.value,
            tier=skill_meta[name].tier.value,
        )
        for name, score in scores.items()
        if name in skill_meta
    ]
    priors.sort(key=lambda item: item.score, reverse=True)
    return priors[:limit]


def inspect_workspace_capabilities(workspace_root: str | Path | None) -> dict[str, Any]:
    """Summarize executable signals available in a workspace."""

    if not workspace_root:
        return {
            "exists": False,
            "root": "",
            "sample_files": [],
            "languages": [],
            "frameworks": [],
            "has_tests": False,
            "suggested_commands": [],
        }

    root = Path(workspace_root)
    if not root.exists():
        return {
            "exists": False,
            "root": str(root),
            "sample_files": [],
            "languages": [],
            "frameworks": [],
            "has_tests": False,
            "suggested_commands": [],
        }

    sample_files: list[str] = []
    suffixes: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        sample_files.append(rel)
        if path.suffix:
            suffixes.append(path.suffix.lower())
        if len(sample_files) >= 12:
            break

    languages: list[str] = []
    if any(item == ".py" for item in suffixes):
        languages.append("python")
    if any(item in {".js", ".ts", ".tsx", ".jsx"} for item in suffixes):
        languages.append("javascript")
    if any(item == ".rs" for item in suffixes):
        languages.append("rust")
    if any(item == ".go" for item in suffixes):
        languages.append("go")

    frameworks: list[str] = []
    if (root / "pyproject.toml").exists() or (root / "pytest.ini").exists() or (root / "tests").exists():
        frameworks.append("pytest")
    if (root / "package.json").exists():
        frameworks.append("npm")
    if (root / "Cargo.toml").exists():
        frameworks.append("cargo")
    if (root / "go.mod").exists():
        frameworks.append("go")

    suggested_commands: list[str] = []
    tests_root = root / "tests"
    if tests_root.exists():
        targeted = [path.relative_to(root).as_posix() for path in sorted(tests_root.rglob("test_*")) if path.is_file()]
        suggested_commands.extend(f"pytest -q {item}" for item in targeted[:2])
        suggested_commands.append("pytest -q")
    if (root / "package.json").exists():
        suggested_commands.append("npm test")
    if (root / "Cargo.toml").exists():
        suggested_commands.append("cargo test")
    if (root / "go.mod").exists():
        suggested_commands.append("go test ./...")

    deduped_commands: list[str] = []
    for item in suggested_commands:
        if item not in deduped_commands:
            deduped_commands.append(item)

    return {
        "exists": True,
        "root": str(root),
        "sample_files": sample_files,
        "languages": languages,
        "frameworks": frameworks,
        "has_tests": bool(tests_root.exists()),
        "suggested_commands": deduped_commands[:5],
    }


def _required_channels_from_packages(package_priors: list[dict[str, Any]]) -> list[str]:
    channels: list[str] = []
    for item in package_priors:
        if not isinstance(item, dict):
            continue
        score = float(item.get("match_score", 0.0) or 0.0)
        if score < 0.52:
            continue
        requirements = [str(req).strip().lower() for req in item.get("runtime_requirements", []) if str(req).strip()] if isinstance(item.get("runtime_requirements", []), list) else []
        tools = [str(tool).strip().lower() for tool in item.get("tool_refs", []) if str(tool).strip()] if isinstance(item.get("tool_refs", []), list) else []
        if "workspace" in requirements or any(tool.startswith("workspace_") for tool in tools):
            channels.append("workspace")
        if any(req in {"web", "evidence", "external"} for req in requirements) or any(tool in {"external_resource_hub", "evidence_dossier_builder"} for tool in tools):
            channels.append("web")
        if "risk" in requirements or any(tool == "policy_risk_matrix" for tool in tools):
            channels.append("risk")
        if item.get("skill_refs") or item.get("tool_refs"):
            channels.append("discovery")
    deduped: list[str] = []
    for channel in channels:
        if channel not in deduped:
            deduped.append(channel)
    return deduped


def _query_requests_data_artifacts(query: str) -> bool:
    markers = [
        "data analysis",
        "analytics",
        "dataset",
        "csv",
        "table",
        "sql",
        "cohort",
        "dataset pull",
        "loader template",
        "data spec",
        "\u6570\u636e\u5206\u6790",
        "\u6570\u636e\u96c6",
        "\u8868\u683c",
    ]
    lowered = str(query or "").lower()
    return _count_markers(lowered, markers) > 0


def _package_graph_expansion_actions(*, package_priors: list[dict[str, Any]], selected_channels: list[str]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    selected = set(selected_channels)
    artifact_map = {
        "patch": "patch_draft",
        "execution_trace": "validation_execution",
        "validation_report": "validation_execution",
        "evidence_pack": "dataset_pull_spec",
        "evidence_bundle": "dataset_pull_spec",
        "chart_pack": "chart_pack_spec",
        "chart": "chart_pack_spec",
        "data_pack": "data_analysis_spec",
        "data": "data_analysis_spec",
        "deck": "slide_deck_plan",
        "slides": "slide_deck_plan",
        "presentation": "slide_deck_plan",
        "webpage": "webpage_blueprint",
        "website": "webpage_blueprint",
    }
    for package in package_priors:
        if not isinstance(package, dict):
            continue
        score = float(package.get("match_score", 0.0) or 0.0)
        if score < 0.58:
            continue
        package_name = str(package.get("name", "package")).strip() or "package"
        artifacts = [str(item).strip().lower() for item in package.get("artifact_kinds", []) if str(item).strip()] if isinstance(package.get("artifact_kinds", []), list) else []
        for artifact in artifacts:
            kind = artifact_map.get(artifact)
            if not kind:
                continue
            if kind in {"dataset_pull_spec"} and "web" not in selected:
                continue
            if kind in {"patch_draft", "validation_execution"} and "workspace" not in selected:
                continue
            actions.append(
                {
                    "kind": kind,
                    "title": kind.replace("_", " ").title(),
                    "depends_on": ["analysis"],
                    "reason": f"skill package {package_name} recommends {artifact} artifacts",
                }
            )
        tools = [str(item).strip() for item in package.get("tool_refs", []) if str(item).strip()] if isinstance(package.get("tool_refs", []), list) else []
        for tool_name in tools:
            lowered = tool_name.lower()
            if lowered in {"external_resource_hub", "evidence_dossier_builder"} and "web" in selected:
                actions.append(
                    {
                        "node_type": "tool_call",
                        "tool_name": tool_name,
                        "tool_args": {"query": f"package-guided collection for {package_name}", "limit": 5},
                        "title": f"Package Probe {tool_name.replace('_', ' ').title()}",
                        "depends_on": ["analysis"],
                        "reason": f"skill package {package_name} recommends {tool_name}",
                    }
                )
            if lowered == "policy_risk_matrix" and "risk" in selected:
                actions.append(
                    {
                        "node_type": "tool_call",
                        "tool_name": tool_name,
                        "tool_args": {"query": f"package-guided risk scan for {package_name}", "evidence_limit": 4},
                        "title": "Package Risk Matrix",
                        "depends_on": ["analysis"],
                        "reason": f"skill package {package_name} recommends explicit risk evaluation",
                    }
                )
    return actions


def requested_output_modes(*, query: str, output_mode: str) -> list[str]:
    """Infer one or more artifact surfaces requested by the user."""

    lowered = str(query or "").lower()
    rows = [
        ("patch", ["patch", "diff", "fix", "implement", "code change", "\u8865\u4e01", "\u4fee\u590d"]),
        ("runbook", ["runbook", "playbook", "operating procedure", "\u64cd\u4f5c\u624b\u518c", "\u9884\u6848"]),
        ("report", ["report", "brief", "memo", "summary", "proposal", "\u62a5\u544a", "\u65b9\u6848", "\u603b\u7ed3"]),
        ("webpage", ["webpage", "website", "landing page", "landing", "html", "frontend", "web app", "\u7f51\u9875", "\u524d\u7aef"]),
        ("slides", ["slides", "slide", "deck", "presentation", "ppt", "keynote", "\u5e7b\u706f", "\u6f14\u793a"]),
        ("chart", ["chart", "charts", "graph", "plot", "visualization", "visualize", "\u56fe\u8868", "\u53ef\u89c6\u5316"]),
        ("podcast", ["podcast", "episode", "audio", "interview", "\u64ad\u5ba2", "\u97f3\u9891"]),
        ("video", ["video", "storyboard", "trailer", "short film", "\u89c6\u9891", "\u5206\u955c"]),
        ("image", ["image", "poster", "illustration", "thumbnail", "render", "\u6d77\u62a5", "\u63d2\u56fe"]),
        ("data", ["data analysis", "analytics", "dataset", "csv", "table", "sql", "cohort", "\u6570\u636e\u5206\u6790", "\u6570\u636e\u96c6"]),
    ]
    requested: list[str] = []
    if output_mode in {name for name, _markers in rows}:
        requested.append(output_mode)
    for name, markers in rows:
        if _count_markers(lowered, markers) > 0 and name not in requested:
            requested.append(name)
    return requested


def _is_report_like_artifact(kind: str) -> bool:
    normalized = str(kind or "").strip()
    if not normalized:
        return False
    if normalized.startswith("custom:"):
        return normalized not in {"custom:checklist", "custom:faq"}
    return normalized in {
        "deliverable_report",
        "evidence_bundle",
        "workspace_findings",
        "risk_register",
    }


def _select_synthesis_skill(
    *,
    query: str,
    primary_artifact_kind: str,
    selected_channels: set[str],
    research_surface: bool,
    contracts: list[dict[str, Any]],
    requested_surface_count: int,
) -> str:
    primary = str(primary_artifact_kind or "").strip()
    support_kinds = {"completion_packet", "delivery_bundle", "evidence_bundle", "workspace_findings"}
    custom_contract_count = sum(
        1 for item in contracts if isinstance(item, dict) and str(item.get("kind", "")).startswith("custom:")
    )
    material_contract_count = sum(
        1
        for item in contracts
        if isinstance(item, dict)
        and str(item.get("kind", "")).strip()
        and str(item.get("kind", "")).strip() not in support_kinds
    )
    report_like_count = sum(
        1
        for item in contracts
        if isinstance(item, dict)
        and _is_report_like_artifact(str(item.get("kind", "")).strip())
        and str(item.get("kind", "")).strip() not in support_kinds
    )
    if primary in {"runbook", "custom:checklist"}:
        return "ops_runbook"
    if custom_contract_count > 0 or requested_surface_count > 1 or material_contract_count > 1:
        return "artifact_synthesis"
    if research_surface and "web" in selected_channels and report_like_count == 1 and _is_report_like_artifact(primary):
        lowered_query = query.lower()
        if any(marker in lowered_query for marker in ["roadmap", "strategy", "improvement", "gaps", "decision"]):
            return "artifact_synthesis"
        return "research_brief"
    if report_like_count > 0 or _is_report_like_artifact(primary):
        if "risk" in selected_channels and "web" not in selected_channels:
            return "ops_runbook"
        return "artifact_synthesis"
    return "artifact_synthesis"


def default_artifact_targets(
    *,
    query: str,
    selected_channels: list[str],
    output_mode: str,
    requires_validation: bool,
    requires_command_execution: bool,
) -> list[str]:
    """Infer artifact targets that make the graph materially reviewable."""

    targets = ["analysis_brief", "completion_packet", "delivery_bundle", "deliverable_report"]
    if "workspace" in selected_channels:
        targets.append("workspace_findings")
    if "web" in selected_channels:
        targets.append("evidence_bundle")
    if "risk" in selected_channels:
        targets.append("risk_register")
    if requires_validation:
        targets.append("validation_plan")
    if requires_command_execution:
        targets.append("execution_trace")
    if output_mode == "patch":
        targets.append("patch_plan")
    elif output_mode == "runbook":
        targets.append("runbook")
    if _query_requests_data_artifacts(query):
        targets.append("data_analysis_spec")
    for mode in requested_output_modes(query=query, output_mode=output_mode):
        targets.extend(
            {
                "webpage": ["webpage_blueprint"],
                "slides": ["slide_deck_plan"],
                "chart": ["chart_pack_spec"],
                "podcast": ["podcast_episode_plan"],
                "video": ["video_storyboard"],
                "image": ["image_prompt_pack"],
                "data": ["data_analysis_spec"],
            }.get(mode, [])
        )
    deduped: list[str] = []
    for item in targets:
        if item not in deduped:
            deduped.append(item)
    return deduped


def custom_artifact_actions(*, task_spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert custom artifact contracts into executable workspace actions."""

    contracts = task_spec.get("artifact_contracts", []) if isinstance(task_spec.get("artifact_contracts", []), list) else []
    target = str(task_spec.get("target", "")).strip().lower()
    actions: list[dict[str, Any]] = []
    for item in contracts:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", "")).strip()
        if not kind.startswith("custom:"):
            continue
        title = str(item.get("title", kind.replace("custom:", "").replace("_", " ").title())).strip()
        format_hint = str(item.get("format_hint", "markdown")).strip() or "markdown"
        slug = re.sub(r"[^a-z0-9]+", "-", kind.replace("custom:", "").lower()).strip("-") or "artifact"
        content_type = "application/json" if format_hint == "json" else "text/markdown"
        relative_path = f"briefs/{slug}.json" if content_type == "application/json" else f"briefs/{slug}.md"
        depends_on = ["analysis"]
        if target == "research" and kind in {
            "custom:memo",
            "custom:brief",
            "custom:executive_memo",
            "custom:decision_memo",
            "custom:launch_memo",
            "custom:one_pager",
        }:
            depends_on = ["analysis", "evidence", "external_resources"]
        actions.append(
            {
                "node_type": "workspace_action",
                "kind": kind,
                "title": f"Generate {title}",
                "depends_on": depends_on,
                "reason": f"query explicitly asks for {title.lower()} as a first-class deliverable",
                "relative_path": relative_path,
                "content_type": content_type,
                "format_hint": format_hint,
                "artifact_contract": {
                    "kind": kind,
                    "title": title,
                    "format_hint": format_hint,
                    "required": bool(item.get("required", True)),
                },
            }
        )
    return actions


def plan_graph_expansion(
    *,
    query: str,
    execution_intent: str,
    output_mode: str,
    selected_channels: list[str],
    workspace_summary: dict[str, Any],
    requires_command_execution: bool,
    live_model_overrides: dict[str, Any] | None,
    skill_priors: list[SkillPrior],
    package_priors: list[dict[str, Any]] | None = None,
    task_spec: dict[str, Any] | None = None,
    capability_plan: dict[str, Any] | None = None,
    execution_loop: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Plan additional executable graph nodes beyond analysis/report writing."""

    local = _default_graph_expansion(
        query=query,
        execution_intent=execution_intent,
        output_mode=output_mode,
        selected_channels=selected_channels,
        workspace_summary=workspace_summary,
        requires_command_execution=requires_command_execution,
        package_priors=package_priors,
        task_spec=task_spec,
        capability_plan=capability_plan,
    )
    loop_context = execution_loop or build_execution_loop(
        query=query,
        task_spec=task_spec or {},
        selected_channels=selected_channels,
        capability_plan=capability_plan or {},
        graph_expansion=local,
        requires_command_execution=requires_command_execution,
    )
    return refine_graph_expansion_with_live_model(
        query=query,
        execution_intent=execution_intent,
        output_mode=output_mode,
        workspace_summary=workspace_summary,
        skill_priors=skill_priors,
        execution_loop=loop_context,
        local=local,
        live_model_overrides=live_model_overrides,
    )


def _default_graph_expansion(
    *,
    query: str,
    execution_intent: str,
    output_mode: str,
    selected_channels: list[str],
    workspace_summary: dict[str, Any],
    requires_command_execution: bool,
    package_priors: list[dict[str, Any]] | None = None,
    task_spec: dict[str, Any] | None = None,
    capability_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    selected = set(selected_channels)
    lowered = str(query or "").lower()
    contracts = task_spec.get("artifact_contracts", []) if isinstance(task_spec, dict) and isinstance(task_spec.get("artifact_contracts", []), list) else []
    contract_kinds = {
        str(item.get("kind", "")).strip()
        for item in contracts
        if isinstance(item, dict) and str(item.get("kind", "")).strip()
    }
    explicit_data_build = any(
        marker in lowered for marker in ["dataset", "data analysis", "csv", "sql", "dashboard", "\u6570\u636e\u5206\u6790", "\u6570\u636e\u96c6"]
    )

    if execution_intent in {"code", "mixed"} or output_mode == "patch":
        actions.append(
            {
                "kind": "patch_scaffold",
                "title": "Generate Patch Scaffold",
                "depends_on": ["analysis"],
                "reason": "code-oriented tasks benefit from an explicit patch scaffold",
            }
        )
        actions.append(
            {
                "kind": "patch_draft",
                "title": "Generate Patch Draft",
                "depends_on": ["analysis"],
                "reason": "code-oriented tasks benefit from a concrete draft patch artifact",
            }
        )
    if "web" in selected and (
        explicit_data_build
        or output_mode == "data"
        or _query_requests_data_artifacts(query)
        or bool(contract_kinds & {"data_analysis_spec", "dataset_pull_spec", "dataset_loader_template"})
    ):
        actions.append(
            {
                "kind": "dataset_pull_spec",
                "title": "Generate Dataset Pull Spec",
                "depends_on": ["analysis"],
                "reason": "external-evidence tasks benefit from a reproducible data collection spec",
            }
        )
        actions.append(
            {
                "kind": "dataset_loader_template",
                "title": "Generate Dataset Loader Template",
                "depends_on": ["analysis"],
                "reason": "external-evidence tasks benefit from a reusable loader template",
            }
        )
    for mode in requested_output_modes(query=query, output_mode=output_mode):
        actions.extend(
            {
                "webpage": [
                    {
                        "kind": "webpage_blueprint",
                        "title": "Generate Webpage Blueprint",
                        "depends_on": ["analysis"],
                        "reason": "page-design tasks need a concrete first-screen and section blueprint",
                    }
                ],
                "slides": [
                    {
                        "kind": "slide_deck_plan",
                        "title": "Generate Slide Deck Plan",
                        "depends_on": ["analysis"],
                        "reason": "presentation tasks need slide-by-slide structure and proof beats",
                    }
                ],
                "chart": [
                    {
                        "kind": "chart_pack_spec",
                        "title": "Generate Chart Pack Spec",
                        "depends_on": ["analysis"],
                        "reason": "visualization tasks need chart choices and data contracts",
                    }
                ],
                "podcast": [
                    {
                        "kind": "podcast_episode_plan",
                        "title": "Generate Podcast Episode Plan",
                        "depends_on": ["analysis"],
                        "reason": "audio tasks need a segment plan and episode arc",
                    }
                ],
                "video": [
                    {
                        "kind": "video_storyboard",
                        "title": "Generate Video Storyboard",
                        "depends_on": ["analysis"],
                        "reason": "video tasks need scene-by-scene storyboard structure",
                    }
                ],
                "image": [
                    {
                        "kind": "image_prompt_pack",
                        "title": "Generate Image Prompt Pack",
                        "depends_on": ["analysis"],
                        "reason": "image tasks need reusable prompt directions and visual constraints",
                    }
                ],
                "data": [
                    {
                        "kind": "data_analysis_spec",
                        "title": "Generate Data Analysis Spec",
                        "depends_on": ["analysis"],
                        "reason": "data-analysis tasks need questions, metrics, cuts, and output contracts",
                    }
                ],
            }.get(mode, [])
        )
    if requires_command_execution and workspace_summary.get("suggested_commands"):
        actions.append(
            {
                "kind": "validation_execution",
                "title": "Execute Suggested Validation",
                "depends_on": ["analysis"],
                "reason": "workspace indicates concrete validation commands are available",
            }
        )
    actions.extend(_package_graph_expansion_actions(package_priors=package_priors or [], selected_channels=selected_channels))
    actions.extend(custom_artifact_actions(task_spec=task_spec or {}))
    for step in (capability_plan or {}).get("steps", []) if isinstance((capability_plan or {}).get("steps", []), list) else []:
        if not isinstance(step, dict) or str(step.get("node_type", "")) != "workspace_action":
            continue
        kind = str(step.get("ref", "")).strip()
        if not kind:
            continue
        actions.append(
            {
                "kind": kind,
                "title": str(step.get("title", kind.replace("_", " ").title())).strip(),
                "depends_on": ["analysis"],
                "reason": str(step.get("reason", "capability graph selected workspace action")).strip(),
            }
        )

    deduped_actions: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for action in actions:
        node_type = str(action.get("node_type", "workspace_action")).strip() or "workspace_action"
        key = str(
            action.get("kind", action.get("tool_name", action.get("subagent_kind", action.get("title", ""))))
        ).strip()
        if not key:
            continue
        dedupe_key = (node_type, key)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped_actions.append(action)

    constrained_nodes = _constrain_live_graph_expansion(
        query=query,
        execution_intent=execution_intent,
        output_mode=output_mode,
        nodes=_normalize_graph_expansion_nodes({"actions": deduped_actions}),
    )
    constrained_actions = [
        {
            "kind": str(item.get("kind", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "depends_on": list(item.get("depends_on", ["analysis"])) if isinstance(item.get("depends_on", []), list) else ["analysis"],
            "reason": str(item.get("reason", "graph expansion")).strip(),
        }
        for item in constrained_nodes
        if str(item.get("node_type", "")) == "workspace_action"
    ]

    return {
        "actions": constrained_actions,
        "nodes": constrained_nodes,
        "replan_enabled": bool(deduped_actions or requires_command_execution),
        "replan_focus": ["execution", "artifacts", "validation"],
        "rationale": ["local graph expansion selected"],
        "source": "local",
    }


def refine_graph_expansion_with_live_model(
    *,
    query: str,
    execution_intent: str,
    output_mode: str,
    workspace_summary: dict[str, Any],
    skill_priors: list[SkillPrior],
    execution_loop: dict[str, Any],
    local: dict[str, Any],
    live_model_overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    """Optionally refine graph expansion with a live model."""

    if not live_model_overrides:
        return local
    try:
        from app.harness.live_agent import CallBudget, LiveModelConfig, LiveModelGateway

        config = LiveModelConfig.resolve(live_model_overrides)
        if not config:
            return local
        gateway = LiveModelGateway(config)
        fallback_seed = _thin_graph_expansion_fallback(local)
        payload = {
            "query": query,
            "execution_intent": execution_intent,
            "output_mode": output_mode,
            "workspace_summary": workspace_summary,
            "skill_priors": [item.to_dict() for item in skill_priors[:4]],
            "execution_loop": execution_loop,
            "fallback_seed": fallback_seed,
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "You are expanding a general agent task graph. "
                    "Return strict JSON with keys: nodes, replan_enabled, replan_focus, rationale. "
                    "Each node must include node_type from workspace_action, tool_call, subagent. "
                    "The execution_loop describes the intended observe -> decide -> act -> deliver progression. "
                    "Treat fallback_seed as a minimal structural fallback, not as a target you must copy. "
                    "Prefer the smallest additions that advance the current loop toward a stronger primary deliverable. "
                    f"Allowed workspace_action kinds: {', '.join(sorted(allowed_workspace_action_kinds(include_internal=True)))}. "
                    "You may also emit kind starting with custom: when you include relative_path plus content_type or artifact_contract. "
                    "Allowed tool_call names: tool_search, workspace_file_search, workspace_file_read, external_resource_hub, "
                    "evidence_dossier_builder, code_experiment_design, policy_risk_matrix. "
                    "Allowed subagent kinds: repair_probe, research_probe, general_probe. "
                    "Only propose nodes that materially improve executable artifacts, evidence gathering, or delivery closure. "
                    "Avoid ornamental support nodes when the request can be satisfied with a shorter path."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
        ]
        text, _meta = gateway.chat(
            messages=messages,
            budget=CallBudget(max_calls=1),
            temperature=0.0,
            require_json=True,
        )
        parsed = _coerce_json_dict(text)
        nodes = _normalize_graph_expansion_nodes(parsed)
        nodes = _constrain_live_graph_expansion(
            query=query,
            execution_intent=execution_intent,
            output_mode=output_mode,
            nodes=nodes,
        )
        if not nodes:
            return fallback_seed
        replan_focus = [str(item).strip() for item in parsed.get("replan_focus", []) if str(item).strip()] if isinstance(parsed.get("replan_focus", []), list) else []
        rationale = list(local.get("rationale", []))
        rationale.append("live model refined graph expansion")
        for item in parsed.get("rationale", []) if isinstance(parsed.get("rationale", []), list) else []:
            text_item = str(item).strip()
            if text_item:
                rationale.append(text_item)
        actions = [
            {
                "kind": str(item.get("kind", "")).strip(),
                "title": str(item.get("title", "")).strip(),
                "depends_on": list(item.get("depends_on", ["analysis"])) if isinstance(item.get("depends_on", []), list) else ["analysis"],
                "reason": str(item.get("reason", "live model expansion")).strip(),
            }
            for item in nodes
            if str(item.get("node_type", "")) == "workspace_action"
        ]
        return {
            "actions": actions,
            "nodes": nodes,
            "replan_enabled": bool(parsed.get("replan_enabled", True)),
            "replan_focus": replan_focus or list(local.get("replan_focus", [])),
            "rationale": rationale[:8],
            "source": "live_model",
        }
    except Exception:
        return _thin_graph_expansion_fallback(local)


def _thin_graph_expansion_fallback(local: dict[str, Any]) -> dict[str, Any]:
    local_actions = local.get("actions", []) if isinstance(local.get("actions", []), list) else []
    actions = [
        {
            "kind": str(item.get("kind", "")).strip(),
            "title": str(item.get("title", "")).strip(),
            "depends_on": list(item.get("depends_on", ["analysis"])) if isinstance(item.get("depends_on", []), list) else ["analysis"],
            "reason": str(item.get("reason", "graph expansion fallback")).strip(),
        }
        for item in local_actions
        if isinstance(item, dict) and str(item.get("kind", "")).strip()
    ]
    nodes = _normalize_graph_expansion_nodes({"actions": actions})
    rationale = list(local.get("rationale", [])) if isinstance(local.get("rationale", []), list) else []
    rationale.append("thin local fallback retained only executable artifact actions")
    return {
        "actions": actions,
        "nodes": nodes,
        "replan_enabled": bool(local.get("replan_enabled", bool(actions))),
        "replan_focus": list(local.get("replan_focus", [])) if isinstance(local.get("replan_focus", []), list) else [],
        "rationale": rationale[:8],
        "source": "local_fallback",
    }


def _constrain_live_graph_expansion(
    *,
    query: str,
    execution_intent: str,
    output_mode: str,
    nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lowered = str(query or "").lower()
    report_like = output_mode in {"report", "artifact"} and any(
        marker in lowered for marker in ["report", "memo", "brief", "research", "\u62a5\u544a", "\u5907\u5fd8\u5f55"]
    )
    explicit_data_build = any(
        marker in lowered for marker in ["dataset", "data analysis", "csv", "sql", "dashboard", "\u6570\u636e\u5206\u6790", "\u6570\u636e\u96c6"]
    )
    explicit_parallel_agent = any(
        marker in lowered for marker in ["subagent", "delegate", "parallel agent", "multi-agent", "research team"]
    )
    presentation_surface = _count_markers(lowered, ["presentation", "slides", "slide", "deck", "webpage", "website", "landing"]) > 0
    allowed_report_custom_kinds = {
        "custom:memo",
        "custom:brief",
        "custom:executive_memo",
        "custom:decision_memo",
        "custom:launch_memo",
        "custom:one_pager",
        "custom:source_matrix",
        "custom:research_outline",
        "custom:direct_answer_baseline",
    }
    filtered: list[dict[str, Any]] = []
    for item in nodes:
        if not isinstance(item, dict):
            continue
        node_type = str(item.get("node_type", "")).strip()
        if report_like and node_type in {"tool_call", "subagent"} and not explicit_parallel_agent and not presentation_surface:
            tool_name = str(item.get("tool_name", "")).strip()
            research_evidence_query = _count_markers(
                lowered,
                ["investigate", "evidence", "latest", "deep-research", "web", "internet", "sources", "citations"],
            ) > 0
            if node_type == "tool_call" and tool_name in {"external_resource_hub", "evidence_dossier_builder"} and research_evidence_query:
                filtered.append(item)
                continue
            continue
        if node_type != "workspace_action":
            filtered.append(item)
            continue
        kind = str(item.get("kind", "")).strip()
        if report_like:
            if kind.startswith("custom:") and kind not in allowed_report_custom_kinds:
                continue
            if kind in {"dataset_pull_spec", "dataset_loader_template", "data_analysis_spec"} and not explicit_data_build:
                continue
        filtered.append(item)
    return filtered


def refine_deliberation_with_live_model(
    *,
    query: str,
    target: str,
    execution_intent: str,
    output_mode: str,
    skill_priors: list[SkillPrior],
    workspace_summary: dict[str, Any],
    execution_loop: dict[str, Any],
    required_channels: list[str],
    local: ChannelDeliberation,
    live_model_overrides: dict[str, Any] | None,
) -> ChannelDeliberation:
    """Optionally refine local channel selection with a live model."""

    if not live_model_overrides:
        return local

    try:
        from app.harness.live_agent import CallBudget, LiveModelConfig, LiveModelGateway

        config = LiveModelConfig.resolve(live_model_overrides)
        if not config:
            return local
        gateway = LiveModelGateway(config)
        payload = {
            "query": query,
            "target": target,
            "execution_intent": execution_intent,
            "output_mode": output_mode,
            "skill_priors": [item.to_dict() for item in skill_priors[:4]],
            "workspace_summary": workspace_summary,
            "execution_loop": execution_loop,
            "required_channels": list(required_channels),
            "local_deliberation": local.to_dict(),
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "You are selecting evidence/action channels for a general agent task planner. "
                    "Return strict JSON with keys: selected_channels, rationale, channel_scores. "
                    "selected_channels must be an array chosen from workspace, web, discovery, risk. "
                    "The execution_loop describes the intended observe -> decide -> act -> deliver progression. "
                    "required_channels are hard structural requirements and must be preserved. "
                    "Choose channels that are genuinely necessary to move that loop forward. "
                    "Use workspace only when local artifacts are likely necessary. "
                    "Use web only when external evidence is likely necessary. "
                    "Prefer discovery for open-ended tasks. "
                    "Avoid over-selecting channels when a shorter path can still produce a strong primary deliverable."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
        ]
        text, _meta = gateway.chat(
            messages=messages,
            budget=CallBudget(max_calls=1),
            temperature=0.0,
            require_json=True,
        )
        parsed = _coerce_json_dict(text)
        raw_selected = parsed.get("selected_channels", [])
        selected = [str(item).strip() for item in raw_selected if str(item).strip() in {"workspace", "web", "discovery", "risk"}]
        selected = list(dict.fromkeys(list(required_channels) + selected))
        if not selected:
            return local
        raw_scores = parsed.get("channel_scores", {})
        llm_scores = {
            key: _safe_float(raw_scores.get(key), 0.88 if key in selected else 0.12)
            for key in {"workspace", "web", "discovery", "risk"}
        }
        merged_scores: dict[str, float] = {}
        for key in {"workspace", "web", "discovery", "risk"}:
            score = llm_scores.get(key, 0.12)
            if key in required_channels:
                score = max(score, 0.82)
            merged_scores[key] = round(min(max(score, 0.0), 1.0), 4)
        rationale = list(local.rationale)
        rationale.append("live model refined channel selection")
        for item in parsed.get("rationale", []) if isinstance(parsed.get("rationale", []), list) else []:
            text_item = str(item).strip()
            if text_item:
                rationale.append(text_item)
        deduped_selected: list[str] = []
        for item in selected:
            if item not in deduped_selected:
                deduped_selected.append(item)
        return ChannelDeliberation(scores=merged_scores, selected=deduped_selected, rationale=rationale[:8])
    except Exception:
        return local


def deliberate_channels(
    *,
    query: str,
    target: str,
    execution_intent: str,
    output_mode: str,
    task_spec: dict[str, Any],
    capability_plan: dict[str, Any],
    skill_priors: list[SkillPrior],
    workspace_root: str | Path | None,
    workspace_signal: int,
    external_signal: int,
    code_signal: int,
    ops_signal: int,
) -> ChannelDeliberation:
    """Choose channels from task/capability structure, with heuristics only as fallback."""
    required_from_task = [
        str(item).strip()
        for item in task_spec.get("required_channels", [])
        if str(item).strip()
    ] if isinstance(task_spec.get("required_channels", []), list) else []
    required_from_capability = [
        str(item).strip()
        for item in capability_plan.get("required_channels", [])
        if str(item).strip()
    ] if isinstance(capability_plan.get("required_channels", []), list) else []
    structured_selected = list(dict.fromkeys(required_from_task + required_from_capability))
    if structured_selected:
        scores = {key: 0.12 for key in {"workspace", "web", "discovery", "risk"}}
        rationale: list[str] = []
        for item in structured_selected:
            if item not in scores:
                continue
            scores[item] = 0.88 if item in required_from_task else 0.76
        if "workspace" in structured_selected and workspace_root and Path(workspace_root).exists():
            scores["workspace"] = max(scores["workspace"], 0.9)
        if "discovery" in structured_selected:
            rationale.append("channel selection follows the task spec and capability graph instead of keyword scoring")
        else:
            rationale.append("capability graph selected the minimum required channels")
        if "workspace" in structured_selected:
            rationale.append("workspace channel is structurally required for local artifact grounding")
        if "web" in structured_selected:
            rationale.append("web channel is structurally required for external evidence")
        if "risk" in structured_selected:
            rationale.append("risk channel is structurally required for governance or safety closure")
        return ChannelDeliberation(
            scores={key: round(value, 4) for key, value in scores.items()},
            selected=structured_selected,
            rationale=rationale[:8],
        )
    return _fallback_deliberate_channels(
        query=query,
        target=target,
        execution_intent=execution_intent,
        output_mode=output_mode,
        skill_priors=skill_priors,
        workspace_root=workspace_root,
        workspace_signal=workspace_signal,
        external_signal=external_signal,
        code_signal=code_signal,
        ops_signal=ops_signal,
    )


def _fallback_deliberate_channels(
    *,
    query: str,
    target: str,
    execution_intent: str,
    output_mode: str,
    skill_priors: list[SkillPrior],
    workspace_root: str | Path | None,
    workspace_signal: int,
    external_signal: int,
    code_signal: int,
    ops_signal: int,
) -> ChannelDeliberation:
    """Minimal structural fallback kept only when no explicit channel requirement exists."""
    del query, target, execution_intent, output_mode, skill_priors, workspace_root, workspace_signal, external_signal, code_signal, ops_signal
    selected = ["discovery"]
    scores = {key: round(0.84 if key == "discovery" else 0.12, 4) for key in {"workspace", "web", "discovery", "risk"}}
    rationale = [
        "no structural channel requirement was inferred, so fallback stayed discovery-only",
        "additional channels should come from live model deliberation or explicit task structure, not local guessing",
    ]
    return ChannelDeliberation(scores=scores, selected=selected, rationale=rationale[:8])


def build_dynamic_task_graph(
    query: str,
    *,
    target: str = "general",
    workspace_root: str | Path = ".",
    profile: TaskProfile | None = None,
    live_model_overrides: dict[str, Any] | None = None,
) -> tuple[TaskProfile, ExecutableTaskGraph]:
    """Compile an executable task graph from a deliberated task profile."""

    resolved = profile or analyze_task_request(
        query,
        target=target,
        workspace_root=workspace_root,
        live_model_overrides=live_model_overrides,
    )
    keywords = resolved.keywords or ["task"]
    slug = _slugify(keywords[:3], fallback=resolved.execution_intent or "task")

    task_contracts = resolved.task_spec.get("artifact_contracts", []) if isinstance(resolved.task_spec.get("artifact_contracts", []), list) else []
    report_title = {
        "patch": "Patch Preparation Report",
        "runbook": "Operational Runbook",
        "report": "Research Report",
        "webpage": "Website Blueprint",
        "slides": "Slide Deck Plan",
        "chart": "Chart Pack Brief",
        "podcast": "Podcast Episode Plan",
        "video": "Video Storyboard",
        "image": "Image Prompt Pack",
        "data": "Data Analysis Pack",
        "artifact": "Executable Task Artifact",
    }.get(resolved.output_mode, "Executable Task Artifact")
    if any(
        str(item.get("kind", "")) in {"custom:memo", "custom:executive_memo", "custom:decision_memo", "custom:launch_memo"}
        for item in task_contracts
        if isinstance(item, dict)
    ):
        report_title = "Research Memo"
    report_path = f"reports/{slug}-{resolved.output_mode}-report.md"

    nodes: list[TaskGraphNode] = [
        TaskGraphNode(
            node_id="scope",
            title="Scope Task",
            node_type="routing",
            status="ready",
            notes=[query],
            metrics={
                "evidence_strategy": resolved.evidence_strategy,
                "execution_intent": resolved.execution_intent,
                "output_mode": resolved.output_mode,
                "reasoning_style": resolved.reasoning_style,
                "domains": list(resolved.domains),
                "keywords": list(keywords[:6]),
                "skill_priors": [item.name for item in resolved.skill_priors],
                "selected_channels": list(resolved.deliberation.selected),
                "channel_scores": dict(resolved.deliberation.scores),
                "channel_rationale": list(resolved.deliberation.rationale),
                "artifact_targets": list(resolved.artifact_targets),
                "workspace_summary": dict(resolved.workspace_summary),
                "task_spec": dict(resolved.task_spec),
                "capability_plan": dict(resolved.capability_plan),
                "graph_expansion": dict(resolved.graph_expansion),
            },
        )
    ]
    analysis_sources = ["scope"]
    selected = set(resolved.deliberation.selected)

    if "discovery" in selected:
        nodes.append(
            TaskGraphNode(
                node_id="capabilities",
                title="Discover Relevant Tools",
                node_type="tool_call",
                status="ready",
                depends_on=["scope"],
                metrics={"tool_name": "tool_search", "tool_args": {"query": query, "limit": 8}},
            )
        )
        analysis_sources.append("capabilities")

    if resolved.skill_priors:
        skill_query = " ".join(keywords[:3]) or resolved.execution_intent or query
        nodes.append(
            TaskGraphNode(
                node_id="skill_priors",
                title="Inspect Skill Priors",
                node_type="tool_call",
                status="ready",
                depends_on=["scope"],
                notes=[f"priors: {', '.join(item.name for item in resolved.skill_priors)}"],
                metrics={"tool_name": "code_skill_search", "tool_args": {"query": skill_query, "limit": 6}},
            )
        )
        analysis_sources.append("skill_priors")

    if "workspace" in selected:
        glob = "*.py" if resolved.execution_intent == "code" else "*"
        focus_query = keywords[0] if keywords else query
        nodes.extend(
            [
                TaskGraphNode(
                    node_id="workspace_scan",
                    title="Inspect Workspace",
                    node_type="workspace_snapshot",
                    status="ready",
                    depends_on=["scope"],
                    metrics={"area": "workspace", "glob": glob, "max_files": 20, "preview_limit": 6},
                ),
                TaskGraphNode(
                    node_id="workspace_focus",
                    title="Find Workspace Signals",
                    node_type="tool_call",
                    status="ready",
                    depends_on=["workspace_scan"],
                    metrics={
                        "tool_name": "workspace_file_search",
                        "tool_args": {"query": focus_query, "glob": glob, "limit": 8},
                    },
                ),
            ]
        )
        analysis_sources.extend(["workspace_scan", "workspace_focus"])
        nodes.append(
            TaskGraphNode(
                node_id="workspace_artifact",
                title="Write Workspace Findings",
                node_type="file_write",
                status="ready",
                depends_on=["workspace_focus"],
                metrics={
                    "area": "outputs",
                    "relative_path": f"artifacts/{slug}-workspace-findings.json",
                    "source_node_id": "workspace_focus",
                    "result_field": "",
                },
            )
        )

    if "web" in selected:
        domains = resolved.domains or ["general"]
        nodes.extend(
            [
                TaskGraphNode(
                    node_id="external_resources",
                    title="Collect External Resources",
                    node_type="tool_call",
                    status="ready",
                    depends_on=["scope"],
                    metrics={"tool_name": "external_resource_hub", "tool_args": {"query": query, "limit": 6}},
                ),
                TaskGraphNode(
                    node_id="evidence",
                    title="Build Evidence Dossier",
                    node_type="tool_call",
                    status="ready",
                    depends_on=["external_resources"],
                    metrics={
                        "tool_name": "evidence_dossier_builder",
                        "tool_args": {"query": query, "limit": 6, "domains": domains},
                    },
                ),
            ]
        )
        analysis_sources.extend(["external_resources", "evidence"])
        nodes.append(
            TaskGraphNode(
                node_id="evidence_artifact",
                title="Write Evidence Bundle",
                node_type="file_write",
                status="ready",
                depends_on=["evidence"],
                metrics={
                    "area": "outputs",
                    "relative_path": f"artifacts/{slug}-evidence-bundle.json",
                    "source_node_id": "evidence",
                    "result_field": "",
                },
            )
        )

    if "risk" in selected:
        nodes.append(
            TaskGraphNode(
                node_id="risk",
                title="Evaluate Risk and Governance",
                node_type="tool_call",
                status="ready",
                depends_on=["scope"],
                metrics={"tool_name": "policy_risk_matrix", "tool_args": {"query": query, "evidence_limit": 4}},
            )
        )
        analysis_sources.append("risk")
        nodes.append(
            TaskGraphNode(
                node_id="risk_artifact",
                title="Write Risk Register",
                node_type="file_write",
                status="ready",
                depends_on=["risk"],
                metrics={
                    "area": "outputs",
                    "relative_path": f"artifacts/{slug}-risk-register.json",
                    "source_node_id": "risk",
                    "result_field": "",
                },
            )
        )

    primary_skill = resolved.skill_priors[0].name if resolved.skill_priors else "decompose_task"
    nodes.append(
        TaskGraphNode(
            node_id="analysis",
            title="Analyze Task",
            node_type="skill_call",
            status="ready",
            depends_on=[node_id for node_id in analysis_sources if node_id != "scope"] or ["scope"],
            metrics={
                "skill_name": primary_skill,
                "source_node_ids": analysis_sources,
                "prompt": query,
            },
        )
    )
    nodes.append(
        TaskGraphNode(
            node_id="analysis_artifact",
            title="Write Analysis Brief",
            node_type="file_write",
            status="ready",
            depends_on=["analysis"],
            metrics={
                "area": "outputs",
                "relative_path": f"artifacts/{slug}-analysis.md",
                "source_node_id": "analysis",
                "result_field": "output",
                "content_prefix": "# Analysis Brief\n\n",
            },
        )
    )

    synthesis_sources = ["analysis"]
    if resolved.requires_validation:
        validation_skill = "validation_planner"
        validation_depends = ["analysis"]
        if "evidence" in analysis_sources:
            validation_depends.append("evidence")
        if "workspace_focus" in analysis_sources:
            validation_depends.append("workspace_focus")
        nodes.append(
            TaskGraphNode(
                node_id="validation",
                title="Plan Validation",
                node_type="skill_call",
                status="ready",
                depends_on=list(dict.fromkeys(validation_depends)),
                metrics={
                    "skill_name": validation_skill,
                    "source_node_ids": validation_depends,
                    "prompt": query,
                },
            )
        )
        synthesis_sources.append("validation")
        nodes.append(
            TaskGraphNode(
                node_id="validation_artifact",
                title="Write Validation Plan",
                node_type="file_write",
                status="ready",
                depends_on=["validation"],
                metrics={
                    "area": "outputs",
                    "relative_path": f"artifacts/{slug}-validation.md",
                    "source_node_id": "validation",
                    "result_field": "output",
                    "content_prefix": "# Validation Plan\n\n",
                },
            )
        )

    if resolved.requires_command_execution and resolved.workspace_summary.get("suggested_commands"):
        command_depends = ["analysis"]
        if "workspace_focus" in analysis_sources:
            command_depends.append("workspace_focus")
        if resolved.requires_validation:
            command_depends.append("validation")
        nodes.append(
            TaskGraphNode(
                node_id="execution",
                title="Execute Suggested Validation",
                node_type="command",
                status="ready",
                depends_on=list(dict.fromkeys(command_depends)),
                commands=list(resolved.workspace_summary.get("suggested_commands", [])),
                metrics={
                    "area": "workspace",
                    "timeout_seconds": 60,
                    "command_count": len(resolved.workspace_summary.get("suggested_commands", [])),
                },
            )
        )
        synthesis_sources.append("execution")

    expansion_action_ids: list[str] = []
    expansion_specs = _normalize_graph_expansion_nodes(resolved.graph_expansion)
    for spec in expansion_specs:
        node_type = str(spec.get("node_type", "workspace_action")).strip() or "workspace_action"
        if node_type == "workspace_action" and str(spec.get("kind", "")).strip() == "validation_execution":
            continue
        depends_on = [str(item) for item in spec.get("depends_on", ["analysis"]) if str(item)]
        if "validation" in node_ids_from_nodes(nodes) and "validation" not in depends_on:
            depends_on.append("validation")
        depends_on = list(dict.fromkeys(depends_on))
        existing_ids = node_ids_from_nodes(nodes)
        action_id = _expansion_node_id(spec, existing_ids)
        if node_type == "workspace_action":
            metrics = {
                "action_kind": str(spec.get("kind", "")).strip(),
                "prompt": query,
                "source_node_ids": list(
                    dict.fromkeys(
                        [str(item) for item in spec.get("source_node_ids", depends_on) if str(item)]
                    )
                )
                or depends_on,
                "workspace_summary": dict(resolved.workspace_summary),
            }
            if str(spec.get("relative_path", "")).strip():
                metrics["relative_path"] = str(spec.get("relative_path", "")).strip()
            if str(spec.get("content_type", "")).strip():
                metrics["content_type"] = str(spec.get("content_type", "")).strip()
            if str(spec.get("format_hint", "")).strip():
                metrics["format_hint"] = str(spec.get("format_hint", "")).strip()
            if isinstance(spec.get("artifact_contract", {}), dict):
                metrics["artifact_contract"] = dict(spec.get("artifact_contract", {}))
        elif node_type == "tool_call":
            metrics = {
                "tool_name": str(spec.get("tool_name", "tool_search")).strip(),
                "tool_args": dict(spec.get("tool_args", {})) if isinstance(spec.get("tool_args", {}), dict) else {},
            }
        else:
            metrics = {
                "subagent_kind": str(spec.get("subagent_kind", "general_probe")).strip(),
                "objective": str(spec.get("objective", query)).strip() or query,
                "prompt": query,
                "source_node_ids": list(
                    dict.fromkeys(
                        [str(item) for item in spec.get("source_node_ids", depends_on) if str(item)]
                    )
                )
                or depends_on,
                "workspace_summary": dict(resolved.workspace_summary),
            }
        nodes.append(
            TaskGraphNode(
                node_id=action_id,
                title=str(
                    spec.get(
                        "title",
                        spec.get("kind", spec.get("tool_name", spec.get("subagent_kind", "Expansion Node"))),
                    )
                ).strip(),
                node_type=node_type,
                status="ready",
                depends_on=depends_on,
                metrics=metrics,
            )
        )
        expansion_action_ids.append(action_id)
        synthesis_sources.append(action_id)

    research_surface = (
        resolved.execution_intent == "research"
        or (resolved.output_mode == "report" and "web" in selected)
    )
    if research_surface and _should_materialize_research_support(query=query, task_spec=resolved.task_spec):
        memo_kinds = {
            "custom:memo",
            "custom:brief",
            "custom:executive_memo",
            "custom:decision_memo",
            "custom:launch_memo",
            "custom:one_pager",
        }
        deferred_memo_node_ids = [
            item.node_id
            for item in nodes
            if isinstance(item, TaskGraphNode)
            and str(item.node_type) == "workspace_action"
            and str(item.metrics.get("action_kind", "")) in memo_kinds
        ]
        research_nodes = [
            (
                "source_matrix",
                "Build Source Matrix",
                "custom:source_matrix",
                f"research/{slug}-source-matrix.md",
                ["Question", "Source", "Usefulness", "Open Gaps"],
            ),
            (
                "report_outline",
                "Build Research Outline",
                "custom:research_outline",
                f"research/{slug}-outline.md",
                ["Core Thesis", "Sections", "Evidence Coverage", "Missing Proof"],
            ),
            (
                "direct_baseline",
                "Draft Direct-Model Baseline",
                "custom:direct_answer_baseline",
                f"research/{slug}-direct-baseline.md",
                ["Baseline Answer", "What It Misses", "What Harness Must Add"],
            ),
        ]
        research_evidence_sources = [
            item.node_id
            for item in nodes
            if isinstance(item, TaskGraphNode)
            and str(item.node_type) in {"tool_call", "skill_call"}
            and (
                item.node_id in {"analysis", "external_resources", "evidence"}
                or str(item.metrics.get("tool_name", "")) in {"external_resource_hub", "evidence_dossier_builder"}
            )
        ]
        prior_sources = list(
            dict.fromkeys(
                [item for item in synthesis_sources if item not in deferred_memo_node_ids]
                + research_evidence_sources
            )
        )
        for node_id, title, kind, relative_path, sections in research_nodes:
            source_ids = list(dict.fromkeys(prior_sources))
            nodes.append(
                TaskGraphNode(
                    node_id=node_id,
                    title=title,
                    node_type="workspace_action",
                    status="ready",
                    depends_on=source_ids,
                    metrics={
                        "action_kind": kind,
                        "prompt": query,
                        "source_node_ids": source_ids,
                        "relative_path": relative_path,
                        "content_type": "text/markdown",
                        "format_hint": "markdown",
                        "artifact_contract": {
                            "title": title,
                            "sections": sections,
                        },
                    },
                )
            )
            prior_sources.append(node_id)
        synthesis_sources = list(dict.fromkeys(prior_sources + deferred_memo_node_ids))
        research_support_ids = ["source_matrix", "report_outline", "direct_baseline"]
        rewritten_nodes: list[TaskGraphNode] = []
        for item in nodes:
            if not isinstance(item, TaskGraphNode):
                rewritten_nodes.append(item)
                continue
            if str(item.node_type) != "workspace_action":
                rewritten_nodes.append(item)
                continue
            action_kind = str(item.metrics.get("action_kind", "")) if isinstance(item.metrics, dict) else ""
            if action_kind not in memo_kinds:
                rewritten_nodes.append(item)
                continue
            memo_depends = list(dict.fromkeys(list(item.depends_on or []) + research_support_ids))
            memo_sources = list(
                dict.fromkeys(
                    list(item.metrics.get("source_node_ids", []))
                    + [node_id for node_id in research_support_ids if node_id]
                )
            )
            rewritten_nodes.append(
                TaskGraphNode(
                    node_id=item.node_id,
                    title=item.title,
                    node_type=item.node_type,
                    status=item.status,
                    depends_on=memo_depends,
                    commands=list(item.commands),
                    notes=list(item.notes),
                    artifacts=list(item.artifacts),
                    metrics={**dict(item.metrics), "source_node_ids": memo_sources},
                )
            )
        nodes = rewritten_nodes

    contracts = resolved.task_spec.get("artifact_contracts", []) if isinstance(resolved.task_spec.get("artifact_contracts", []), list) else []
    requested_surface_count = len(requested_output_modes(query=query, output_mode=resolved.output_mode))
    primary_artifact_kind = str(resolved.task_spec.get("primary_artifact_kind", "")).strip()
    synthesis_skill = _select_synthesis_skill(
        query=query,
        primary_artifact_kind=primary_artifact_kind,
        selected_channels=selected,
        research_surface=research_surface,
        contracts=contracts,
        requested_surface_count=requested_surface_count,
    )

    nodes.append(
        TaskGraphNode(
            node_id="synthesis",
            title="Synthesize Deliverable",
            node_type="skill_call",
            status="ready",
            depends_on=synthesis_sources,
            metrics={
                "skill_name": synthesis_skill,
                "primary_artifact_kind": primary_artifact_kind,
                "source_node_ids": synthesis_sources,
                "prompt": query,
            },
        )
    )
    nodes.append(
        TaskGraphNode(
            node_id="report",
            title=f"Write {report_title}",
            node_type="file_write",
            status="ready",
            depends_on=["synthesis"],
            metrics={
                "area": "outputs",
                "relative_path": report_path,
                "source_node_id": "synthesis",
                "result_field": "output",
                "content_prefix": f"# {report_title}\n\n",
            },
        )
    )
    if resolved.requires_command_execution and resolved.workspace_summary.get("suggested_commands"):
        nodes.append(
            TaskGraphNode(
                node_id="execution_trace",
                title="Write Execution Trace",
                node_type="file_write",
                status="ready",
                depends_on=["execution"],
                metrics={
                    "area": "outputs",
                    "relative_path": f"artifacts/{slug}-execution-trace.json",
                    "source_node_id": "execution",
                    "result_field": "",
                },
            )
        )

    completion_packet_depends = list(dict.fromkeys(synthesis_sources + ["report"]))
    nodes.append(
        TaskGraphNode(
            node_id="completion_packet",
            title="Generate Completion Packet",
            node_type="workspace_action",
            status="ready",
            depends_on=completion_packet_depends,
            metrics={
                "action_kind": "completion_packet",
                "prompt": query,
                "source_node_ids": completion_packet_depends,
                "workspace_summary": dict(resolved.workspace_summary),
                "task_spec": dict(resolved.task_spec),
            },
        )
    )

    if bool(resolved.graph_expansion.get("replan_enabled", False)):
        replan_depends = ["completion_packet"]
        nodes.append(
            TaskGraphNode(
                node_id="replan",
                title="Replan Graph",
                node_type="graph_replan",
                status="ready",
                depends_on=replan_depends,
                metrics={
                    "prompt": query,
                    "source_node_ids": replan_depends,
                    "replan_focus": list(resolved.graph_expansion.get("replan_focus", [])),
                    "workspace_summary": dict(resolved.workspace_summary),
                    "task_spec": dict(resolved.task_spec),
                    "capability_plan": dict(resolved.capability_plan),
                    "execution_loop": dict(resolved.execution_loop),
                    "graph_expansion_source": str(resolved.graph_expansion.get("source", "local")),
                },
            )
        )

    delivery_bundle_depends = ["completion_packet", "report"]
    if resolved.requires_command_execution and resolved.workspace_summary.get("suggested_commands"):
        delivery_bundle_depends.append("execution_trace")
    nodes.append(
        TaskGraphNode(
            node_id="delivery_bundle",
            title="Generate Delivery Bundle",
            node_type="workspace_action",
            status="ready",
            depends_on=list(dict.fromkeys(delivery_bundle_depends)),
            metrics={
                "action_kind": "delivery_bundle",
                "prompt": query,
                "source_node_ids": list(dict.fromkeys(delivery_bundle_depends)),
                "workspace_summary": dict(resolved.workspace_summary),
                "task_spec": dict(resolved.task_spec),
            },
        )
    )

    phased_nodes: list[TaskGraphNode] = []
    for item in nodes:
        metrics = dict(item.metrics)
        metrics.setdefault("loop_phase", _loop_phase_for_node(item))
        phased_nodes.append(
            TaskGraphNode(
                node_id=item.node_id,
                title=item.title,
                node_type=item.node_type,
                status=item.status,
                depends_on=list(item.depends_on),
                commands=list(item.commands),
                notes=list(item.notes),
                artifacts=list(item.artifacts),
                metrics=metrics,
            )
        )

    graph = ExecutableTaskGraph(
        graph_id=f"task-{slug}",
        mission_type=f"{resolved.execution_intent or 'general'}_task",
        query=query,
        nodes=phased_nodes,
        metadata={
            "execution_loop": dict(resolved.execution_loop),
            "primary_artifact_kind": primary_artifact_kind,
            "selected_channels": list(resolved.deliberation.selected),
            "output_mode": resolved.output_mode,
        },
    )
    return resolved, graph


def _should_materialize_research_support(*, query: str, task_spec: dict[str, Any]) -> bool:
    lowered = str(query or "").lower()
    contracts = task_spec.get("artifact_contracts", []) if isinstance(task_spec.get("artifact_contracts", []), list) else []
    kinds = {
        str(item.get("kind", "")).strip()
        for item in contracts
        if isinstance(item, dict) and str(item.get("kind", "")).strip()
    }
    explicit_markers = [
        "source matrix",
        "research outline",
        "direct baseline",
        "baseline answer",
        "compare with direct answer",
    ]
    support_kinds = {"custom:memo", "custom:brief", "custom:executive_memo", "custom:decision_memo", "custom:launch_memo"}
    return bool((kinds & support_kinds) or any(marker in lowered for marker in explicit_markers))


def _loop_phase_for_node(node: TaskGraphNode) -> str:
    node_id = str(node.node_id or "").strip()
    node_type = str(node.node_type or "").strip()
    metrics = node.metrics if isinstance(node.metrics, dict) else {}
    action_kind = str(metrics.get("action_kind", "")).strip()

    observe_ids = {
        "scope",
        "capabilities",
        "skill_priors",
        "workspace_scan",
        "workspace_focus",
        "workspace_artifact",
        "external_resources",
        "evidence",
        "evidence_artifact",
        "risk",
        "risk_artifact",
    }
    decide_ids = {"analysis", "analysis_artifact", "validation", "validation_artifact", "replan"}
    deliver_ids = {"synthesis", "report", "execution_trace", "completion_packet", "delivery_bundle"}

    if node_id in observe_ids:
        return "observe"
    if node_id in decide_ids:
        return "decide"
    if node_id in deliver_ids:
        return "deliver"
    if node_type == "workspace_action" and action_kind in {"completion_packet", "delivery_bundle"}:
        return "deliver"
    if node_type in {"tool_call", "workspace_snapshot"}:
        return "observe"
    if node_type in {"skill_call"}:
        return "decide"
    if node_type in {"workspace_action", "command", "subagent"}:
        return "act"
    return "act"


def _coerce_json_dict(text: str) -> dict[str, Any]:
    if not text:
        return {}
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {}
        try:
            payload = json.loads(match.group(0))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}


def _safe_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(fallback)


def _normalize_graph_expansion_nodes(payload: dict[str, Any]) -> list[dict[str, Any]]:
    allowed_workspace_actions = allowed_workspace_action_kinds(include_internal=True)
    allowed_tool_names = {
        "tool_search",
        "workspace_file_search",
        "workspace_file_read",
        "external_resource_hub",
        "evidence_dossier_builder",
        "code_experiment_design",
        "policy_risk_matrix",
    }
    allowed_subagent_kinds = {"repair_probe", "research_probe", "general_probe"}

    raw_nodes: list[dict[str, Any]] = []
    nodes_payload = payload.get("nodes", [])
    if isinstance(nodes_payload, list):
        raw_nodes.extend(item for item in nodes_payload if isinstance(item, dict))
    actions_payload = payload.get("actions", [])
    if isinstance(actions_payload, list):
        for item in actions_payload:
            if not isinstance(item, dict):
                continue
            if str(item.get("node_type", "")).strip():
                raw_nodes.append(item)
            else:
                raw_nodes.append({**item, "node_type": "workspace_action"})

    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in raw_nodes:
        node_type = str(item.get("node_type", "workspace_action")).strip() or "workspace_action"
        depends_on = [str(dep).strip() for dep in item.get("depends_on", ["analysis"]) if str(dep).strip()] if isinstance(item.get("depends_on", []), list) else ["analysis"]
        reason = str(item.get("reason", "graph expansion")).strip() or "graph expansion"
        title = str(item.get("title", "")).strip()

        if node_type == "workspace_action":
            kind = str(item.get("kind", "")).strip()
            is_custom = kind.startswith("custom:")
            if kind in {"completion_packet", "delivery_bundle"}:
                continue
            if kind not in allowed_workspace_actions and not is_custom:
                continue
            if is_custom and not (
                str(item.get("relative_path", "")).strip()
                or isinstance(item.get("artifact_contract", {}), dict)
            ):
                continue
            key = (node_type, kind)
            if key in seen:
                continue
            seen.add(key)
            node_spec = {
                "node_type": node_type,
                "kind": kind,
                "title": title or kind.replace("_", " ").title(),
                "depends_on": depends_on,
                "reason": reason,
                "source_node_ids": list(
                    item.get("source_node_ids", depends_on)
                    if isinstance(item.get("source_node_ids", depends_on), list)
                    else depends_on
                ),
            }
            if is_custom:
                node_spec["relative_path"] = str(item.get("relative_path", "")).strip()
                node_spec["content_type"] = str(item.get("content_type", "")).strip()
                node_spec["format_hint"] = str(item.get("format_hint", "")).strip()
                if isinstance(item.get("artifact_contract", {}), dict):
                    node_spec["artifact_contract"] = dict(item.get("artifact_contract", {}))
            normalized.append(node_spec)
            continue

        if node_type == "tool_call":
            tool_name = str(item.get("tool_name", "")).strip()
            if tool_name not in allowed_tool_names:
                continue
            key = (node_type, tool_name)
            if key in seen:
                continue
            seen.add(key)
            tool_args = dict(item.get("tool_args", {})) if isinstance(item.get("tool_args", {}), dict) else {}
            normalized.append(
                {
                    "node_type": node_type,
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "title": title or tool_name.replace("_", " ").title(),
                    "depends_on": depends_on,
                    "reason": reason,
                }
            )
            continue

        if node_type == "subagent":
            subagent_kind = str(item.get("subagent_kind", "")).strip() or "general_probe"
            if subagent_kind not in allowed_subagent_kinds:
                continue
            key = (node_type, subagent_kind)
            if key in seen:
                continue
            seen.add(key)
            normalized.append(
                {
                    "node_type": node_type,
                    "subagent_kind": subagent_kind,
                    "objective": str(item.get("objective", "")).strip(),
                    "title": title or subagent_kind.replace("_", " ").title(),
                    "depends_on": depends_on,
                    "reason": reason,
                    "source_node_ids": list(
                        item.get("source_node_ids", depends_on)
                        if isinstance(item.get("source_node_ids", depends_on), list)
                        else depends_on
                    ),
                }
            )
    return normalized


def _expansion_node_id(spec: dict[str, Any], existing_ids: set[str]) -> str:
    node_type = str(spec.get("node_type", "workspace_action")).strip() or "workspace_action"
    key = str(
        spec.get("kind", spec.get("tool_name", spec.get("subagent_kind", spec.get("title", "node"))))
    ).strip()
    prefix = {"workspace_action": "action", "tool_call": "tool", "subagent": "subagent"}.get(node_type, "node")
    base = f"{prefix}_{_slugify([key], fallback='node')}"
    candidate = base
    suffix = 2
    while candidate in existing_ids:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def node_ids_from_nodes(nodes: list[TaskGraphNode]) -> set[str]:
    return {item.node_id for item in nodes}


