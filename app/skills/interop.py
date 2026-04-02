"""Interoperability export layer for OpenAI/Anthropic skill ecosystems."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.state import SkillMetadata
from app.ecosystem.marketplace import list_marketplace_skill_metadata
from app.harness.manifest import ToolManifestRegistry
from app.skills.registry import list_builtin_skills, list_external_skills

INTEROP_SCHEMA = "agent-skills-interop/v1"
FRAMEWORKS = {"openai", "anthropic"}


def _slugify_skill_name(name: str) -> str:
    raw = name.strip().lower().replace("_", "-")
    raw = re.sub(r"[^a-z0-9-]+", "-", raw)
    raw = re.sub(r"-{2,}", "-", raw).strip("-")
    if not raw:
        return "skill"
    if len(raw) > 64:
        raw = raw[:64].strip("-")
    if not raw:
        return "skill"
    return raw


def _render_yaml_frontmatter(
    name: str,
    description: str,
    compatibility: str,
    metadata: dict[str, str],
    allowed_tools: list[str],
) -> str:
    lines = ["---"]
    lines.append(f"name: {name}")
    lines.append(f'description: "{description}"')
    lines.append(f'compatibility: "{compatibility}"')
    lines.append("metadata:")
    for key in sorted(metadata.keys()):
        value = metadata[key].replace('"', "'")
        lines.append(f'  {key}: "{value}"')
    if allowed_tools:
        lines.append(f"allowed-tools: {' '.join(allowed_tools)}")
    lines.append("---")
    return "\n".join(lines)


def _framework_compatibility(framework: str) -> str:
    if framework == "openai":
        return "Designed for OpenAI agent clients that support the Agent Skills specification."
    return "Designed for Anthropic Claude clients that support the Agent Skills specification."


def _framework_metadata(framework: str) -> dict[str, str]:
    if framework == "openai":
        return {"framework_target": "openai", "ecosystem": "codex-skills"}
    return {"framework_target": "anthropic", "ecosystem": "claude-skills"}


def _build_description(meta: SkillMetadata) -> str:
    keywords = ", ".join(meta.confidence_keywords[:4]) if meta.confidence_keywords else meta.category.value
    base = (meta.description or meta.summary or f"Skill: {meta.name}").strip()
    text = f"{base}. Use when task keywords include: {keywords}."
    text = text.replace("\n", " ").strip()
    if len(text) > 1000:
        text = text[:1000].rstrip(". ") + "."
    return text


def _tool_fit_score(meta: SkillMetadata, tool: dict[str, Any]) -> float:
    tags = set(str(item).lower() for item in tool.get("tags", []))
    intents = set(str(item).lower() for item in tool.get("intents", []))
    caps = set(str(item).lower() for item in tool.get("capabilities", []))
    words = set(str(item).lower() for item in meta.confidence_keywords)
    words.update(str(item).lower() for item in meta.strengths)
    words.add(meta.category.value.lower())
    overlap = len(words & (tags | intents | caps))

    score = float(overlap) * 0.12
    score += float(tool.get("reliability_score", 0.8)) * 0.25
    score += float(tool.get("novelty_score", 0.5)) * 0.10
    score += max(0.0, 2.0 - float(tool.get("latency_score", 1.0))) * 0.08
    return score


def _suggest_allowed_tools(meta: SkillMetadata, include_harness_tools: bool = True, limit: int = 3) -> list[str]:
    if not include_harness_tools:
        return []

    manifests = ToolManifestRegistry().as_catalog()
    ranked = sorted(
        manifests,
        key=lambda item: _tool_fit_score(meta, item),
        reverse=True,
    )
    out = [str(item.get("name", "")) for item in ranked[: max(1, limit)] if item.get("name")]
    return out


def _build_body(meta: SkillMetadata, allowed_tools: list[str]) -> str:
    strengths = meta.strengths or ["specialized task handling"]
    weaknesses = meta.weaknesses or ["requires context quality checks"]
    synergies = meta.synergies or []
    examples = meta.confidence_keywords[:4]

    lines = [f"# {meta.name}", ""]
    lines.append("## When To Use")
    lines.append(f"- Use this skill when the request needs: {', '.join(strengths[:3])}.")
    if examples:
        lines.append(f"- Trigger hints: {', '.join(examples)}.")
    lines.append("")
    lines.append("## Output Contract")
    lines.append(f"- Output type: {meta.output_type}.")
    lines.append(f"- Tier: {meta.tier.value}; category: {meta.category.value}.")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("- Validate critical claims before finalizing responses.")
    lines.append(f"- Known limitations: {', '.join(weaknesses[:2])}.")
    lines.append("")
    if synergies:
        lines.append("## Synergies")
        lines.append(f"- Works well with: {', '.join(synergies[:4])}.")
        lines.append("")
    if allowed_tools:
        lines.append("## Suggested Harness Tools")
        for item in allowed_tools:
            lines.append(f"- {item}")
        lines.append("")
    lines.append("## Execution Notes")
    lines.append("- Keep responses concise, structured, and auditable.")
    return "\n".join(lines).strip() + "\n"


def _source_map(include_marketplace: bool, include_external: bool) -> list[tuple[SkillMetadata, str]]:
    rows: list[tuple[SkillMetadata, str]] = []
    seen: set[str] = set()

    for meta in list_builtin_skills():
        if meta.name in seen:
            continue
        rows.append((meta, "builtin"))
        seen.add(meta.name)

    if include_external:
        for meta in list_external_skills():
            if meta.name in seen:
                continue
            rows.append((meta, "external"))
            seen.add(meta.name)

    if include_marketplace:
        for meta in list_marketplace_skill_metadata():
            if meta.name in seen:
                continue
            rows.append((meta, "marketplace"))
            seen.add(meta.name)

    return rows


def export_interop_catalog(
    framework: str,
    include_marketplace: bool = True,
    include_external: bool = True,
    include_harness_tools: bool = True,
) -> dict[str, Any]:
    """Build compatibility catalog for one framework target."""

    target = framework.strip().lower()
    if target not in FRAMEWORKS:
        raise ValueError(f"Unsupported framework: {framework}")

    rows = _source_map(include_marketplace=include_marketplace, include_external=include_external)
    skills: list[dict[str, Any]] = []
    framework_meta = _framework_metadata(target)
    for meta, source in rows:
        slug = _slugify_skill_name(meta.name)
        description = _build_description(meta)
        allowed_tools = _suggest_allowed_tools(meta, include_harness_tools=include_harness_tools)
        md_meta = {
            "original_name": meta.name,
            "owner": meta.owner,
            "source": source,
            "version": meta.version,
            "category": meta.category.value,
            "tier": meta.tier.value,
            "output_type": meta.output_type,
            **framework_meta,
        }
        frontmatter = _render_yaml_frontmatter(
            name=slug,
            description=description,
            compatibility=_framework_compatibility(target),
            metadata=md_meta,
            allowed_tools=allowed_tools,
        )
        body = _build_body(meta, allowed_tools=allowed_tools)
        skill_md = f"{frontmatter}\n\n{body}"
        skills.append(
            {
                "name": slug,
                "original_name": meta.name,
                "source": source,
                "description": description,
                "metadata": md_meta,
                "allowed_tools": allowed_tools,
                "skill_md": skill_md,
            }
        )

    return {
        "schema": INTEROP_SCHEMA,
        "framework": target,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "skill_count": len(skills),
        "skills": skills,
    }


def export_interop_all(
    include_marketplace: bool = True,
    include_external: bool = True,
    include_harness_tools: bool = True,
) -> dict[str, Any]:
    """Build compatibility catalogs for both OpenAI and Anthropic targets."""

    outputs = {}
    for name in sorted(FRAMEWORKS):
        outputs[name] = export_interop_catalog(
            framework=name,
            include_marketplace=include_marketplace,
            include_external=include_external,
            include_harness_tools=include_harness_tools,
        )
    return {
        "schema": INTEROP_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frameworks": outputs,
    }


def write_interop_bundle(payload: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    """Write compatibility payload into reusable skill folders + index files."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    if "frameworks" in payload:
        outputs: dict[str, Any] = {}
        for framework, data in payload.get("frameworks", {}).items():
            outputs[framework] = write_interop_bundle(data, root / framework)
        index = root / "interop_bundle.json"
        index.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return {
            "root": str(root),
            "index": str(index),
            "frameworks": outputs,
        }

    framework = str(payload.get("framework", "unknown"))
    framework_root = root
    skills_root = framework_root / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)

    index_rows: list[dict[str, Any]] = []
    for skill in payload.get("skills", []):
        if not isinstance(skill, dict):
            continue
        name = str(skill.get("name", "skill"))
        skill_dir = skills_root / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text(str(skill.get("skill_md", "")), encoding="utf-8")
        index_rows.append(
            {
                "name": name,
                "original_name": skill.get("original_name", ""),
                "source": skill.get("source", ""),
                "description": skill.get("description", ""),
                "path": str(skill_path),
                "allowed_tools": skill.get("allowed_tools", []),
            }
        )

    index = framework_root / "skills_index.json"
    index_payload = {
        "schema": INTEROP_SCHEMA,
        "framework": framework,
        "generated_at": payload.get("generated_at", ""),
        "skill_count": len(index_rows),
        "skills": index_rows,
    }
    index.write_text(json.dumps(index_payload, indent=2, default=str), encoding="utf-8")
    raw = framework_root / "skills_raw.json"
    raw.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return {
        "framework": framework,
        "root": str(framework_root),
        "skills_root": str(skills_root),
        "index": str(index),
        "raw": str(raw),
        "skill_count": len(index_rows),
    }
