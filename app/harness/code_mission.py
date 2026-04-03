"""Engineering-focused mission-pack artifacts for code and implementation work."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.harness.models import HarnessRun

_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "reports",
    "data",
    ".pytest_cache",
}
_TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".go",
    ".rs",
    ".sh",
}
_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "into",
    "from",
    "this",
    "that",
    "your",
    "have",
    "will",
    "should",
    "about",
    "design",
    "create",
    "build",
    "make",
    "need",
}


@dataclass(frozen=True)
class RepoFileMatch:
    path: str
    score: float
    anchors: list[str]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "score": round(self.score, 4),
            "anchors": list(self.anchors),
            "rationale": self.rationale,
        }


class CodeMissionPackBuilder:
    """Build engineering mission packs with patch/test/trace/validation artifacts."""

    def build(
        self,
        query: str,
        run: HarnessRun,
        run_summary: dict[str, Any],
        workspace: str | Path = ".",
    ) -> dict[str, Any]:
        root = Path(workspace).resolve()
        tokens = self._query_tokens(query)
        candidates = self._rank_files(root=root, tokens=tokens)
        selected = candidates[:4]
        tests = self._find_tests(root=root, candidates=selected)
        commands = self._validation_commands(root=root, tests=tests)
        trace = self._execution_trace(run_summary)
        patch = self._patch_artifact(query=query, matches=selected, tests=tests)
        validation = self._validation_report(
            commands=commands,
            tests=tests,
            matches=selected,
            trace=trace,
            evidence=run_summary.get("evidence", {}),
        )
        return {
            "schema": "agent-harness-code-mission/v1",
            "query": query,
            "workspace": str(root),
            "primary_deliverable": "Code mission pack with patch plan, validation path, and execution trace.",
            "candidate_files": [item.to_dict() for item in selected],
            "patch": patch,
            "tests": {
                "targeted_files": tests,
                "commands": commands,
            },
            "execution_trace": trace,
            "validation_report": validation,
        }

    def _rank_files(self, root: Path, tokens: list[str], limit: int = 12) -> list[RepoFileMatch]:
        matches: list[RepoFileMatch] = []
        for path in root.rglob("*"):
            if path.is_dir():
                if path.name in _SKIP_DIRS:
                    continue
                continue
            if any(part in _SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() not in _TEXT_SUFFIXES:
                continue
            rel = path.relative_to(root).as_posix()
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            score, anchors = self._score_file(rel, content, tokens)
            if score <= 0:
                continue
            rationale = f"matched {len(anchors)} token anchors against query intent"
            matches.append(RepoFileMatch(path=rel, score=score, anchors=anchors[:4], rationale=rationale))
        matches.sort(key=lambda item: item.score, reverse=True)
        return matches[:limit]

    @staticmethod
    def _score_file(rel: str, content: str, tokens: list[str]) -> tuple[float, list[str]]:
        lowered_path = rel.lower()
        lowered_lines = content.lower().splitlines()
        score = 0.0
        anchors: list[str] = []
        for token in tokens:
            if token in lowered_path:
                score += 1.2
                anchors.append(f"path:{token}")
            for idx, line in enumerate(lowered_lines[:220], start=1):
                if token in line:
                    score += 0.35
                    anchors.append(f"L{idx}:{line.strip()[:80]}")
                    break
        return score, anchors

    @staticmethod
    def _query_tokens(query: str) -> list[str]:
        tokens: list[str] = []
        for raw in query.lower().replace("/", " ").replace("-", " ").split():
            token = "".join(ch for ch in raw if ch.isalnum() or ch == "_")
            if len(token) < 3 or token in _STOPWORDS:
                continue
            if token not in tokens:
                tokens.append(token)
        return tokens[:10]

    @staticmethod
    def _find_tests(root: Path, candidates: list[RepoFileMatch]) -> list[str]:
        tests_root = root / "tests"
        if not tests_root.exists():
            return []
        rows: list[str] = []
        stems = {Path(item.path).stem.lower().replace("test_", "") for item in candidates}
        for path in tests_root.rglob("test_*"):
            if path.is_dir():
                continue
            rel = path.relative_to(root).as_posix()
            name = path.stem.lower()
            if any(stem and stem in name for stem in stems):
                rows.append(rel)
        return rows[:6]

    @staticmethod
    def _validation_commands(root: Path, tests: list[str]) -> list[str]:
        commands: list[str] = []
        if (root / "tests").exists():
            if tests:
                commands.extend(f"pytest -q {item}" for item in tests[:3])
            commands.append("pytest -q")
        if (root / "package.json").exists():
            commands.append("npm test")
        if (root / "Cargo.toml").exists():
            commands.append("cargo test")
        if (root / "go.mod").exists():
            commands.append("go test ./...")
        deduped: list[str] = []
        for item in commands:
            if item not in deduped:
                deduped.append(item)
        return deduped[:6]

    @staticmethod
    def _execution_trace(run_summary: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for step in run_summary.get("steps", [])[:8]:
            rows.append(
                {
                    "step": int(step.get("step", 0)),
                    "tool": str(step.get("tool", "")),
                    "source": str(step.get("source", "")),
                    "success": bool(step.get("success", False)),
                    "latency_ms": float(step.get("latency_ms", 0.0)),
                    "notes": list(step.get("notes", []))[:3],
                }
            )
        return rows

    @staticmethod
    def _patch_artifact(query: str, matches: list[RepoFileMatch], tests: list[str]) -> dict[str, Any]:
        file_plans: list[dict[str, Any]] = []
        diff_lines: list[str] = []
        for item in matches[:3]:
            file_plans.append(
                {
                    "file": item.path,
                    "change_type": "modify",
                    "rationale": item.rationale,
                    "anchors": item.anchors[:3],
                    "tentative_edits": [
                        f"Align implementation in {item.path} with query intent: {query[:120]}",
                        "Add or tighten validation / error handling where the behavior is underspecified.",
                    ],
                }
            )
            diff_lines.extend(
                [
                    f"*** Update File: {item.path}",
                    "@@",
                    f"- existing behavior around {item.anchors[0] if item.anchors else 'target location'}",
                    f"+ revised behavior aligned to: {query[:80]}",
                ]
            )
        return {
            "status": "draft",
            "file_plans": file_plans,
            "targeted_test_files": tests[:3],
            "patch_stub": "*** Begin Patch\n" + "\n".join(diff_lines) + ("\n*** End Patch" if diff_lines else "\n*** End Patch"),
        }

    @staticmethod
    def _validation_report(
        commands: list[str],
        tests: list[str],
        matches: list[RepoFileMatch],
        trace: list[dict[str, Any]],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        blockers: list[str] = []
        if not matches:
            blockers.append("No candidate source files were found for this query.")
        if not commands:
            blockers.append("No project-level validation command could be inferred.")
        status = "ready" if not blockers else "needs_review"
        return {
            "status": status,
            "checks": [
                "candidate source files identified",
                "targeted or project-level validation command inferred",
                "execution trace captured",
                "evidence packet attached where available",
            ],
            "blockers": blockers,
            "evidence_support": {
                "record_count": int(evidence.get("record_count", 0)),
                "citation_count": int(evidence.get("citation_count", 0)),
            },
            "trace_depth": len(trace),
            "targeted_tests": len(tests),
        }
