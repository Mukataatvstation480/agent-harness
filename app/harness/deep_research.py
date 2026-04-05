"""Deep research report builder for repository-level capability studies."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.harness.evidence import EvidenceProviderRegistry
from app.harness.manifest import ToolManifestRegistry
from app.skills.registry import list_builtin_skills


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class HarnessDeepResearchBuilder:
    SCHEMA = "agent-harness-deep-research/v1"

    def __init__(self) -> None:
        self.evidence = EvidenceProviderRegistry()
        self.manifests = ToolManifestRegistry()

    def build(
        self,
        *,
        topic: str,
        subject_root: str | Path,
        competitor_root: str | Path | None = None,
        subject_name: str = "agent-harness",
        competitor_name: str = "deer-flow",
    ) -> dict[str, Any]:
        subject_path = Path(subject_root).resolve()
        competitor_path = Path(competitor_root).resolve() if competitor_root else None
        subject = self._scan_subject_repo(subject_name, subject_path)
        competitor = self._scan_competitor_repo(competitor_name, competitor_path) if competitor_path else {}
        dimensions = self._build_dimensions(subject, competitor)
        surface_map = self._build_surface_map(subject, competitor)
        roadmap = self._build_roadmap(dimensions)
        evidence = self.evidence.collect(
            query=topic,
            limit=8,
            domains=["research", "evidence", "governance", "enterprise"],
        )
        payload = {
            "schema": self.SCHEMA,
            "generated_at": _utc_now(),
            "topic": topic,
            "subject": subject,
            "competitor": competitor,
            "dimensions": dimensions,
            "surface_map": surface_map,
            "roadmap": roadmap,
            "evidence": evidence,
        }
        payload["summary"] = self._executive_summary(subject, competitor, dimensions)
        payload["framework_markdown"] = self._render_framework_markdown(topic, subject, competitor, dimensions, surface_map)
        payload["report_markdown"] = self._render_report_markdown(topic, subject, competitor, dimensions, surface_map, roadmap, evidence)
        return payload

    def write_bundle(self, payload: dict[str, Any], output_dir: str | Path = "reports") -> dict[str, str]:
        root = Path(output_dir).resolve()
        root.mkdir(parents=True, exist_ok=True)
        framework_path = root / "agent_harness_deep_research_framework.md"
        report_path = root / "agent_harness_deep_research_report.md"
        bundle_path = root / "agent_harness_deep_research_bundle.json"
        html_path = root / "agent_harness_deep_research.html"
        framework_path.write_text(str(payload.get("framework_markdown", "")), encoding="utf-8")
        report_path.write_text(str(payload.get("report_markdown", "")), encoding="utf-8")
        bundle_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        html_path.write_text(self.render_html(payload), encoding="utf-8")
        return {
            "framework": str(framework_path),
            "report": str(report_path),
            "bundle": str(bundle_path),
            "html": str(html_path),
        }

    def render_html(self, payload: dict[str, Any]) -> str:
        summary = payload.get("summary", {}) if isinstance(payload.get("summary", {}), dict) else {}
        subject = payload.get("subject", {}) if isinstance(payload.get("subject", {}), dict) else {}
        competitor = payload.get("competitor", {}) if isinstance(payload.get("competitor", {}), dict) else {}
        dimensions = payload.get("dimensions", []) if isinstance(payload.get("dimensions", []), list) else []
        surface_map = payload.get("surface_map", []) if isinstance(payload.get("surface_map", []), list) else []
        roadmap = payload.get("roadmap", []) if isinstance(payload.get("roadmap", []), list) else []
        evidence = payload.get("evidence", {}).get("records", []) if isinstance(payload.get("evidence", {}), dict) else []
        excerpt = str(payload.get("report_markdown", ""))[:2200]
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><title>AI Agent Harness Deep Research</title><style>:root{{--bg:#f5efe4;--panel:rgba(255,251,245,.94);--ink:#132238;--muted:#5d6a7b;--line:rgba(19,34,56,.12);--accent:#cf5c36;--accent2:#2c7a7b;--gold:#cc9a06;--shadow:0 22px 60px rgba(19,34,56,.10)}}*{{box-sizing:border-box}}body{{margin:0;color:var(--ink);font-family:'Segoe UI',sans-serif;background:radial-gradient(circle at top left,rgba(207,92,54,.15),transparent 28%),radial-gradient(circle at top right,rgba(44,122,123,.18),transparent 24%),linear-gradient(180deg,#fffaf1 0%,var(--bg) 100%)}}.page{{max-width:1320px;margin:0 auto;padding:28px}}.hero{{border-radius:28px;padding:32px;background:linear-gradient(135deg,rgba(207,92,54,.18),rgba(44,122,123,.12),rgba(19,34,56,.05));border:1px solid var(--line);box-shadow:var(--shadow)}}.k{{text-transform:uppercase;letter-spacing:.14em;font-size:12px;color:var(--accent2)}}h1{{margin:10px 0 12px;font-size:46px;line-height:1.05}}.lede{{max-width:920px;line-height:1.7;font-size:18px;color:var(--muted)}}.hero-grid{{display:grid;grid-template-columns:1.35fr .95fr;gap:18px;margin-top:18px}}.mini,.card{{background:var(--panel);border:1px solid var(--line);border-radius:22px;padding:20px;box-shadow:var(--shadow)}}.mini{{background:rgba(255,255,255,.56)}}.grid{{display:grid;grid-template-columns:repeat(12,1fr);gap:16px;margin-top:18px}}.s4{{grid-column:span 4}}.s5{{grid-column:span 5}}.s6{{grid-column:span 6}}.s7{{grid-column:span 7}}.s12{{grid-column:span 12}}.ey{{font-size:12px;letter-spacing:.10em;text-transform:uppercase;color:#4a8399}}.metric{{font-size:36px;font-weight:700;margin-top:8px}}.muted{{color:var(--muted)}}ul{{padding-left:18px;margin:10px 0 0}}li{{margin:8px 0;line-height:1.55}}table{{width:100%;border-collapse:collapse;margin-top:12px}}th,td{{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:#456c82}}.ahead{{color:var(--accent2);font-weight:700}}.behind{{color:var(--accent);font-weight:700}}.mixed{{color:var(--gold);font-weight:700}}pre{{white-space:pre-wrap;line-height:1.55;background:rgba(19,34,56,.04);border-radius:18px;padding:18px;overflow:auto}}@media (max-width:980px){{.hero-grid,.grid{{grid-template-columns:1fr}}.s4,.s5,.s6,.s7,.s12{{grid-column:span 1}}h1{{font-size:34px}}}}</style></head><body><div class="page"><section class="hero"><div class="k">Deep Research Demo</div><h1>{html.escape(str(summary.get('title', 'AI Agent Harness Deep Research Report')))}</h1><div class="lede">{html.escape(str(summary.get('summary', '')))}</div><div class="hero-grid"><div class="mini"><div class="ey">Bottom Line</div><ul>{''.join(f'<li>{html.escape(item)}</li>' for item in summary.get('highlights', [])) or '<li>No highlights generated.</li>'}</ul></div><div class="mini"><div class="ey">Why This Matters</div><ul><li>{html.escape(str(summary.get('value_statement', '')))}</li><li>{html.escape(str(summary.get('differentiator', '')))}</li></ul></div></div></section><section class="grid"><div class="card s4"><div class="ey">Agent Harness</div><div class="metric">{int(subject.get('metrics', {}).get('python_files', 0))}</div><div class="muted">Python files scanned</div><ul>{''.join(f'<li>{html.escape(item)}</li>' for item in subject.get('headline_points', []))}</ul></div><div class="card s4"><div class="ey">DeerFlow</div><div class="metric">{int(competitor.get('metrics', {}).get('public_skill_count', 0))}</div><div class="muted">Public skills in reference repo</div><ul>{''.join(f'<li>{html.escape(item)}</li>' for item in competitor.get('headline_points', []))}</ul></div><div class="card s4"><div class="ey">Delivery Surface</div><div class="metric">{int(subject.get('metrics', {}).get('tool_count', 0))}</div><div class="muted">Builtin tools in the delivery runtime</div><ul><li>{html.escape(str(summary.get('delivery_statement', '')))}</li></ul></div><div class="card s7"><div class="ey">Competitive Matrix</div><table><thead><tr><th>Dimension</th><th>Agent Harness</th><th>DeerFlow</th><th>Verdict</th></tr></thead><tbody>{''.join(self._html_dimension_row(item) for item in dimensions)}</tbody></table></div><div class="card s5"><div class="ey">Surface Map</div><table><thead><tr><th>Surface</th><th>Agent Harness</th><th>DeerFlow</th></tr></thead><tbody>{''.join(self._html_surface_row(item) for item in surface_map)}</tbody></table></div><div class="card s6"><div class="ey">Roadmap</div><ul>{''.join(f"<li><strong>{html.escape(str(item.get('phase', '')))}</strong>: {html.escape(str(item.get('focus', '')))}</li>" for item in roadmap)}</ul></div><div class="card s6"><div class="ey">Evidence</div><ul>{''.join(f"<li><strong>{html.escape(str(item.get('title', '')))}</strong>: {html.escape(str(item.get('summary', '')))}</li>" for item in evidence[:8]) or '<li>No evidence records found.</li>'}</ul></div><div class="card s12"><div class="ey">Report Excerpt</div><pre>{html.escape(excerpt)}</pre></div></section></div></body></html>"""

    @staticmethod
    def _html_dimension_row(item: dict[str, Any]) -> str:
        verdict = str(item.get("verdict", "mixed"))
        css = {"ahead": "ahead", "behind": "behind", "mixed": "mixed"}.get(verdict, "mixed")
        return f"<tr><td>{html.escape(str(item.get('label', '')))}</td><td>{float(item.get('subject_score', 0.0)):.1f}</td><td>{float(item.get('competitor_score', 0.0)):.1f}</td><td class='{css}'>{html.escape(verdict)}</td></tr>"

    @staticmethod
    def _html_surface_row(item: dict[str, Any]) -> str:
        return f"<tr><td>{html.escape(str(item.get('surface', '')))}</td><td>{html.escape(str(item.get('subject', '')))}</td><td>{html.escape(str(item.get('competitor', '')))}</td></tr>"
    def _scan_subject_repo(self, name: str, root: Path) -> dict[str, Any]:
        app_root = root / "app"
        core_root = app_root / "core"
        tests_root = root / "tests"
        runtime_text = self._read_text(app_root / "agents" / "runtime.py")
        engine_text = self._read_text(app_root / "harness" / "engine.py")
        tools_text = self._read_text(app_root / "harness" / "tools.py")
        scheduler_text = self._read_text(app_root / "agents" / "scheduler.py")
        main_text = self._read_text(app_root / "main.py")
        tasking_text = self._read_text(core_root / "tasking.py")
        feature_flags = {
            "thread_runtime": "class AgentThreadRuntime" in runtime_text,
            "resume_retry_interrupt": all(token in runtime_text for token in ["resume_execution", "retry_execution", "request_interrupt"]),
            "scheduler_recovery": "recover_execution" in scheduler_text and "recover_all" in scheduler_text,
            "task_graph_runtime": "execute_thread_generic_task" in engine_text and "task_graph_builder" in tools_text,
            "workspace_actions": all(token in tools_text for token in ["workspace_file_search", "workspace_file_read", "workspace_file_write"]),
            "subagent_executor": (app_root / "agents" / "subagents.py").exists(),
            "workspace_view": (app_root / "agents" / "workspace_view.py").exists(),
            "interop_export": (app_root / "skills" / "interop.py").exists(),
            "evidence_provider": (app_root / "harness" / "evidence.py").exists(),
            "deep_research_report": (app_root / "harness" / "deep_research.py").exists(),
            "task_spec_runtime": "TaskSpec" in tasking_text and "CapabilityNode" in tasking_text,
            "gateway_surface": (app_root / "gateway").exists(),
        }
        notable_files = [
            {"path": "app/agents/runtime.py", "reason": "Persistent thread runtime with async wait, resume, retry, and interrupt support."},
            {"path": "app/agents/task_actions.py", "reason": "Maps task-graph nodes into tool, skill, workspace, file, and command actions."},
            {"path": "app/harness/tools.py", "reason": "Holds tool discovery, workspace tools, evidence tools, and executable task-graph generation."},
            {"path": "app/core/tasking.py", "reason": "Defines TaskSpec, artifact contracts, capability graph planning, and workspace action contracts."},
            {"path": "app/harness/deep_research.py", "reason": "Generates research framework, final report, and HTML publication page for repo studies."},
            {"path": "app/skills/interop.py", "reason": "Exports capability catalogs into external skill ecosystems."},
        ]
        workspace_operator_count = sum(1 for token in ["workspace_file_search", "workspace_file_read", "workspace_file_write"] if token in tools_text)
        return {
            "name": name,
            "root": str(root),
            "metrics": {
                "python_files": len(list(app_root.rglob("*.py"))),
                "test_file_count": len(list(tests_root.glob("test_*.py"))),
                "cli_command_count": main_text.count('@app.command("'),
                "builtin_skill_count": len(list_builtin_skills()),
                "tool_count": len(self.manifests.list_all()),
                "workspace_operator_count": workspace_operator_count,
            },
            "feature_flags": feature_flags,
            "headline_points": [
                "The runtime is thread-first: execution state, resume/retry/interrupt controls, and task graph semantics live in first-class modules.",
                "Delivery is no longer just prose generation; the same runtime can emit workspace actions, artifacts, and evidence-backed bundles.",
                "The main gap is product expression: the repo often has stronger internals than what its first-screen deliverables currently show.",
            ],
            "notable_files": notable_files,
        }

    def _scan_competitor_repo(self, name: str, root: Path) -> dict[str, Any]:
        readme_text = self._read_text(root / "README.md")
        backend_root = root / "backend"
        frontend_root = root / "frontend"
        public_skills = root / "skills" / "public"
        return {
            "name": name,
            "root": str(root),
            "metrics": {
                "public_skill_count": len([item for item in public_skills.iterdir() if item.is_dir()]) if public_skills.exists() else 0,
                "backend_test_count": len(list((backend_root / "tests").rglob("test_*.py"))) if (backend_root / "tests").exists() else 0,
            },
            "feature_flags": {
                "subagents": "sub-agent" in readme_text.lower() or "subagent" in readme_text.lower(),
                "memory": "memory" in readme_text.lower(),
                "sandbox": "sandbox" in readme_text.lower(),
                "mcp": "mcp" in readme_text.lower(),
                "frontend_workspace": (frontend_root / "src" / "app" / "workspace").exists() or "workspace" in self._read_text(frontend_root / "CLAUDE.md").lower(),
                "artifact_ui": "artifacts" in self._read_text(frontend_root / "CLAUDE.md").lower(),
                "official_website": "official website" in readme_text.lower(),
                "skill_installation": "install" in readme_text.lower() and "skill" in readme_text.lower(),
            },
            "headline_points": [
                "DeerFlow ships a more productized public surface with workspace, artifacts, thread chat, and gateway-style framing.",
                "Its published skills encode a recognizable research method instead of looking like raw tool wrappers.",
                "The repo is organized like a harness product first, not a collection of experimental modules.",
            ],
            "notable_files": [
                {"path": "README.md", "reason": "Public product positioning around super agent harness, sub-agents, memory, sandboxes, MCP, and demos."},
                {"path": "skills/public/deep-research/SKILL.md", "reason": "Enforces broad exploration, deep dive, diversity validation, and synthesis before content generation."},
                {"path": "skills/public/consulting-analysis/SKILL.md", "reason": "Separates analysis framework generation from final consulting-grade output."},
                {"path": "frontend/CLAUDE.md", "reason": "Describes the thread-based streaming UI with artifacts, workspace, memory, and skills management."},
                {"path": "backend/CLAUDE.md", "reason": "Shows production-harness layers for sandbox, MCP, memory, subagents, and gateway APIs."},
            ],
        }

    def _build_dimensions(self, subject: dict[str, Any], competitor: dict[str, Any]) -> list[dict[str, Any]]:
        s = subject.get("feature_flags", {})
        c = competitor.get("feature_flags", {})
        sm = subject.get("metrics", {})
        cm = competitor.get("metrics", {})
        rows = [
            {
                "label": "Runtime Closure",
                "subject_score": self._score([s.get("thread_runtime", False), s.get("resume_retry_interrupt", False), s.get("scheduler_recovery", False), s.get("task_graph_runtime", False), s.get("workspace_actions", False), s.get("subagent_executor", False)]),
                "competitor_score": self._score([c.get("subagents", False), c.get("sandbox", False), c.get("memory", False), c.get("frontend_workspace", False), c.get("artifact_ui", False), c.get("mcp", False)]),
                "why": "agent-harness now exposes stronger explicit runtime semantics, while DeerFlow still turns more of that runtime into a polished end-user loop.",
            },
            {
                "label": "Capability Packaging",
                "subject_score": self._score([s.get("task_spec_runtime", False), s.get("interop_export", False), sm.get("builtin_skill_count", 0) >= 12, sm.get("tool_count", 0) >= 10, s.get("deep_research_report", False)]),
                "competitor_score": self._score([c.get("skill_installation", False), cm.get("public_skill_count", 0) >= 8, c.get("mcp", False), c.get("official_website", False), c.get("subagents", False)]),
                "why": "Agent Harness is stronger when capabilities are expressed as task specs, artifacts, and exportable catalogs; DeerFlow is still easier to understand from the outside.",
            },
            {
                "label": "Evidence And Governance",
                "subject_score": self._score([s.get("evidence_provider", False), s.get("task_graph_runtime", False), s.get("workspace_view", False), sm.get("test_file_count", 0) >= 8, s.get("deep_research_report", False)]),
                "competitor_score": self._score([c.get("artifact_ui", False), c.get("frontend_workspace", False), c.get("official_website", False), c.get("subagents", False), c.get("memory", False)]),
                "why": "agent-harness is building a stronger evidence-backed delivery spine, but DeerFlow communicates operating trust more clearly through product surfaces.",
            },
            {
                "label": "Workspace Product Surface",
                "subject_score": self._score([s.get("workspace_actions", False), s.get("workspace_view", False), s.get("thread_runtime", False), s.get("gateway_surface", False)]),
                "competitor_score": self._score([c.get("sandbox", False), c.get("mcp", False), c.get("subagents", False), c.get("frontend_workspace", False), c.get("artifact_ui", False)]),
                "why": "DeerFlow still leads on visible workspace, artifact board, and operator UX; agent-harness has the backbone but not enough first-screen legibility.",
            },
            {
                "label": "Result Surface",
                "subject_score": self._score([s.get("deep_research_report", False), s.get("interop_export", False), sm.get("cli_command_count", 0) >= 8, sm.get("workspace_operator_count", 0) >= 3]),
                "competitor_score": self._score([c.get("official_website", False), c.get("frontend_workspace", False), c.get("artifact_ui", False), c.get("skill_installation", False)]),
                "why": "DeerFlow still wins on polish and recognizability; agent-harness needs first-screen outputs that sell the runtime advantage immediately.",
            },
        ]
        for item in rows:
            delta = float(item["subject_score"]) - float(item["competitor_score"])
            item["delta"] = round(delta, 2)
            item["verdict"] = "ahead" if delta >= 0.35 else "behind" if delta <= -0.35 else "mixed"
        return rows

    @staticmethod
    def _score(flags: list[bool]) -> float:
        return round(5.0 * (sum(1 for flag in flags if flag) / max(len(flags), 1)), 1)

    @staticmethod
    def _build_surface_map(subject: dict[str, Any], competitor: dict[str, Any]) -> list[dict[str, str]]:
        s = subject.get("feature_flags", {})
        c = competitor.get("feature_flags", {})
        return [
            {
                "surface": "Thread Runtime",
                "subject": "Explicit thread execution with resume/retry/interrupt." if s.get("thread_runtime") else "Not clearly surfaced.",
                "competitor": "Thread and sub-agent workspace are visible in product docs." if c.get("frontend_workspace") else "Not clearly surfaced.",
            },
            {
                "surface": "Workspace Actions",
                "subject": "Workspace reads, writes, and search are part of the runtime action set." if s.get("workspace_actions") else "Limited workspace action coverage.",
                "competitor": "Workspace is exposed as a user-facing operating surface." if c.get("frontend_workspace") else "Limited evidence in repo scan.",
            },
            {
                "surface": "Artifacts",
                "subject": "Task specs and delivery bundles define output contracts." if s.get("task_spec_runtime") else "Artifacts are not strongly typed.",
                "competitor": "Artifacts are visible in the frontend workspace." if c.get("artifact_ui") else "Artifact UX is not obvious from the repo scan.",
            },
            {
                "surface": "Provider Layer",
                "subject": "Interop export and runtime tooling exist, but gateway productization is still uneven." if s.get("interop_export") else "Provider/export layer is still thin.",
                "competitor": "Sandbox and MCP story are already present in public docs." if c.get("sandbox") or c.get("mcp") else "Provider layer is not clearly surfaced.",
            },
        ]

    @staticmethod
    def _build_roadmap(dimensions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        behind = [item for item in dimensions if item.get("verdict") == "behind"]
        mixed = [item for item in dimensions if item.get("verdict") == "mixed"]
        top_gap = behind[0]["label"] if behind else (mixed[0]["label"] if mixed else "Result Surface")
        return [
            {"phase": "Phase 1 - Sharpen The First Deliverable", "focus": "Make final reports, patch packs, and operating plans noticeably better than a direct one-shot model answer.", "target": top_gap},
            {"phase": "Phase 2 - Turn Skills Into Execution Modules", "focus": "Let skills declare evidence needs, artifact outputs, and validation gates instead of acting like prompt snippets.", "target": "Capability Packaging"},
            {"phase": "Phase 3 - Productize Threads And Workspace", "focus": "Expose thread events, artifact views, workspace controls, and operator interventions as a coherent runtime surface.", "target": "Workspace Product Surface"},
            {"phase": "Phase 4 - Push The Thread-First Advantage", "focus": "Use the same executable task graph for research, engineering, analysis, and operations so the framework stays truly general-purpose.", "target": "Runtime Closure"},
        ]

    def _executive_summary(self, subject: dict[str, Any], competitor: dict[str, Any], dimensions: list[dict[str, Any]]) -> dict[str, Any]:
        ahead = [item["label"] for item in dimensions if item.get("verdict") == "ahead"]
        behind = [item["label"] for item in dimensions if item.get("verdict") == "behind"]
        mixed = [item["label"] for item in dimensions if item.get("verdict") == "mixed"]
        return {
            "title": "AI Agent Harness: Deep Research And Improvement Report",
            "summary": "This report studies the current `agent-harness` codebase against DeerFlow's public structure and concludes that the repo now has a materially stronger thread-first execution core than before, but it still needs clearer deliverable quality and a more legible product surface before it can credibly claim to beat DeerFlow as a general-agent harness.",
            "highlights": [
                f"Current lead: {ahead[0]}." if ahead else "No dimension is yet clearly dominant enough to declare victory.",
                f"Main deficit: {behind[0]}." if behind else "Main deficit is concentrated in mixed, still-unsettled dimensions.",
                f"Critical mixed zone: {mixed[0]}." if mixed else "Most dimensions currently separate clearly.",
            ],
            "value_statement": "The real differentiator is not another demo workflow. It is the ability to turn a request into an executable task graph, keep state across retries and interruptions, and export the result as a deliverable bundle.",
            "differentiator": "If agent-harness sharpens final deliverables while keeping the same thread-first runtime across task families, it can beat skill-first repos on both engineering rigor and product utility.",
            "delivery_statement": "The system is strongest when it converts planning into typed artifacts, workspace actions, and evidence-backed delivery rather than scoreboards.",
        }

    def _render_framework_markdown(self, topic: str, subject: dict[str, Any], competitor: dict[str, Any], dimensions: list[dict[str, Any]], surface_map: list[dict[str, str]]) -> str:
        dimension_rows = "\n".join(f"| {item['label']} | {item['subject_score']:.1f} | {item['competitor_score']:.1f} | {item['verdict']} | {item['why']} |" for item in dimensions)
        surface_rows = "\n".join(f"| {item['surface']} | {item['subject']} | {item['competitor']} |" for item in surface_map)
        return f"""# AI Agent Harness Deep Research Framework

## Research Subject
- Topic: {topic}
- Primary target: {subject.get('name', 'agent-harness')}
- Comparator: {competitor.get('name', 'deer-flow')}
- Objective: determine whether `agent-harness` is structurally competitive with DeerFlow, where it is already ahead, and what must change next to become a genuinely strong general-agent harness.

## Core Questions
1. What is `agent-harness` actually good at today beyond proposal-style output?
2. Where does DeerFlow still lead in public product surface, skill methodology, and operator experience?
3. Which improvements would create engineering value and academic value at the same time?
4. What would make the final deliverable materially better than a direct one-shot model answer?

## Evidence Plan
- Codebase scan of `app/`, `tests/`, and runtime-specific modules in `agent-harness`
- Public structure scan of DeerFlow README, backend/frontend docs, and public skills
- Internal evidence registry output for governance, research, and interoperability references
- Delivery-surface mapping across threads, workspace, artifacts, providers, and skill packaging

## Comparison Axes
| Dimension | Agent Harness | DeerFlow | Verdict | Interpretation |
|---|---:|---:|---|---|
{dimension_rows}

## Surface Map
| Surface | Agent Harness | DeerFlow |
|---|---|---|
{surface_rows}

## Deliverables
1. A deep research report with explicit strengths, deficits, and roadmap
2. A structured JSON evidence bundle for downstream demos or UI rendering
3. A result-first HTML page that surfaces the bottom line before internal mechanics
"""
    def _render_report_markdown(
        self,
        topic: str,
        subject: dict[str, Any],
        competitor: dict[str, Any],
        dimensions: list[dict[str, Any]],
        surface_map: list[dict[str, str]],
        roadmap: list[dict[str, Any]],
        evidence: dict[str, Any],
    ) -> str:
        summary = self._executive_summary(subject, competitor, dimensions)
        strengths = [item for item in dimensions if item.get("verdict") == "ahead"]
        deficits = [item for item in dimensions if item.get("verdict") == "behind"]
        mixed = [item for item in dimensions if item.get("verdict") == "mixed"]
        evidence_rows = evidence.get("records", []) if isinstance(evidence.get("records", []), list) else []
        strengths_block = "\n".join(f"- **{item['label']}** ({item['subject_score']:.1f} vs {item['competitor_score']:.1f}): {item['why']}" for item in strengths) or "- No dimension is ahead by a decisive margin yet."
        deficits_block = "\n".join(f"- **{item['label']}** ({item['subject_score']:.1f} vs {item['competitor_score']:.1f}): {item['why']}" for item in deficits) or "- No dimension is behind by a decisive margin, but several are still mixed."
        mixed_block = "\n".join(f"- **{item['label']}** ({item['subject_score']:.1f} vs {item['competitor_score']:.1f}): {item['why']}" for item in mixed) or "- No mixed dimensions."
        roadmap_lines = "\n".join(f"### {item['phase']}\n- Focus: {item['focus']}\n- Primary target: {item['target']}" for item in roadmap)
        evidence_lines = "\n".join(f"- **{row.get('title', '')}**: {row.get('summary', '')} ({row.get('url', row.get('path', ''))})" for row in evidence_rows[:8])
        surface_lines = "\n".join(f"- **{row['surface']}**: agent-harness -> {row['subject']} | DeerFlow -> {row['competitor']}" for row in surface_map)
        subject_files = "\n".join(f"- `{row['path']}`: {row['reason']}" for row in subject.get("notable_files", [])[:6])
        competitor_files = "\n".join(f"- `{row['path']}`: {row['reason']}" for row in competitor.get("notable_files", [])[:5])
        return f"""# AI Agent Harness Deep Research And Improvement Report

## Executive Summary
{summary['summary']}

- One-line diagnosis: `agent-harness` is no longer just a routing experiment, but it is still not yet a convincingly superior general-agent product when judged against DeerFlow's public surface.
- Why users might still choose it: the framework now has a clearer execution core built around persistent threads, executable task graphs, workspace-bound actions, evidence-backed delivery, and interoperability exports.
- Why users would still hesitate: several of those strengths are still more visible in code than in the first-screen user deliverable.

## Method
This report uses repository-level evidence rather than marketing copy. The analysis covers the live `agent-harness` codebase, the local DeerFlow reference repository, the built-in evidence registry, and a surface-level comparison of threads, workspace, artifacts, and provider packaging.

Topic studied: {topic}

## What Agent Harness Is Today
`agent-harness` has moved closer to a real harness because it now has three things that matter:

1. **Explicit execution semantics**  
   Persistent thread runtime, task-graph execution, node action mapping, async wait, resume, retry, interrupt, and recovery are not hand-waved.
2. **Cross-scene execution primitives**  
   The same runtime can already express tool calls, skill calls, workspace inspection, file writes, command execution, and typed deliverables.
3. **Delivery-aware packaging**  
   The repo can frame requests as task specs, artifact contracts, evidence bundles, and interoperable exports instead of leaving everything as raw chat output.

Key supporting files:
{subject_files}

## Where DeerFlow Still Wins
DeerFlow is ahead in the places users notice first:

1. **Public product surface**  
   It exposes a stronger website, a thread-based frontend workspace, artifact views, memory, skill management, and a more coherent super-agent story.
2. **Skill methodology**  
   Its public `deep-research` and `consulting-analysis` skills communicate a recognizable method instead of reading like generic tool wrappers.
3. **Production framing**  
   The repo is organized as a full harness product with sandbox modes, MCP integration, gateway-oriented layers, and frontend/backend docs that explain the system architecture.

Key supporting DeerFlow files:
{competitor_files}

## Competitive Assessment
### Structural Strengths Where Agent Harness Is Ahead
{strengths_block}

### Structural Deficits Where Agent Harness Is Behind
{deficits_block}

### Mixed Dimensions That Decide The Next Stage
{mixed_block}

## Surface-Level Comparison
{surface_lines}

## The Real Opportunity To Beat DeerFlow
The most defensible path is **not** to imitate DeerFlow skill-for-skill. The better path is to push a different center of gravity:

1. **Make Executable Task Graph the core intermediate representation**  
   One graph should drive research, code, operations, and enterprise workflows with explicit artifacts, retry semantics, and validation hooks.
2. **Turn skills from prompt snippets into graph-aware capability modules**  
   A strong skill in this system should not only describe how to think; it should specify what evidence to collect, what artifact to emit, and what validation gate to pass.
3. **Make the final deliverable obviously better than a direct model answer**  
   That means richer artifacts, clearer evidence injection, stronger repair loops, and less internal score chatter in the user-facing surface.

## Algorithmic Assessment
The strongest algorithmic idea in `agent-harness` today is the move toward a **stateful, resumable task graph runtime** rather than a pure chat loop. That is a real systems contribution because it gives the framework interruption-safe execution, node-level artifact contracts, cross-scene action unification, and a credible path to general-purpose agent execution.

The biggest algorithmic weakness is that the current skill layer is still too heuristic and text-heavy. Until more skills become execution-aware and evidence-aware, the framework's internal semantics will remain stronger than its final outputs.

## Recommended Roadmap
{roadmap_lines}

## Evidence References
{evidence_lines if evidence_lines else '- No registry evidence records were returned.'}

## Why This Report Matters
If `agent-harness` follows the roadmap above, its differentiator becomes clear:
- A single thread-first runtime that can operate across research, engineering, and operations tasks.
- Typed delivery bundles that make artifacts inspectable instead of burying value inside internal traces.
- A more defensible bridge between academic-style reasoning quality and real execution closure.

## Honest Boundary
Today, DeerFlow still has the more legible public product. Agent Harness has the more interesting runtime direction. It wins only if it turns that runtime advantage into outputs that a user can recognize as stronger within the first screen.
"""

    @staticmethod
    def _read_text(path: Path) -> str:
        if not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
