"""Engineering-focused mission-pack artifacts for code and implementation work."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.task_graph import ExecutableTaskGraph, TaskGraphArtifact, TaskGraphNode
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
        execute_validation: bool = False,
        validation_timeout_seconds: int = 180,
        max_validation_commands: int = 3,
    ) -> dict[str, Any]:
        root = Path(workspace).resolve()
        tokens = self._query_tokens(query)
        candidates = self._rank_files(root=root, tokens=tokens)
        selected = candidates[:4]
        tests = self._find_tests(root=root, candidates=selected)
        commands = self._validation_commands(root=root, tests=tests)
        trace = self._execution_trace(run_summary)
        patch_snapshot = self._collect_patch_snapshot(root=root, matches=selected)
        workspace_snapshot = self._workspace_snapshot(root=root, matches=selected, patch_snapshot=patch_snapshot)
        patch = self._patch_artifact(
            query=query,
            matches=selected,
            tests=tests,
            patch_snapshot=patch_snapshot,
        )
        executions = self._run_validation_commands(
            root=root,
            commands=commands,
            enabled=execute_validation,
            timeout_seconds=validation_timeout_seconds,
            limit=max_validation_commands,
        )
        validation = self._validation_report(
            commands=commands,
            tests=tests,
            matches=selected,
            trace=trace,
            evidence=run_summary.get("evidence", {}),
            executions=executions,
            execute_validation=execute_validation,
        )
        task_graph = self._task_graph(
            query=query,
            matches=selected,
            tests=tests,
            commands=commands,
            trace=trace,
            patch=patch,
            validation=validation,
            workspace_snapshot=workspace_snapshot,
            execute_validation=execute_validation,
        )
        return {
            "schema": "agent-harness-code-mission/v1",
            "query": query,
            "workspace": str(root),
            "primary_deliverable": "Code mission pack with executable task graph, patch artifact, validation path, and execution trace.",
            "workspace_snapshot": workspace_snapshot,
            "candidate_files": [item.to_dict() for item in selected],
            "patch": patch,
            "tests": {
                "targeted_files": tests,
                "commands": commands,
            },
            "execution_trace": trace,
            "validation_report": validation,
            "task_graph": task_graph,
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
            if "__pycache__" in path.parts or path.suffix.lower() not in {".py", ".js", ".ts"}:
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
    def _collect_patch_snapshot(root: Path, matches: list[RepoFileMatch]) -> dict[str, Any]:
        if shutil.which("git") is None:
            return {
                "available": False,
                "status": "unavailable",
                "changed_files": [],
                "diff": "",
                "diff_excerpt": [],
            }
        paths = [item.path for item in matches[:6]]
        diff_command = ["git", "-C", str(root), "diff", "--unified=0"]
        if paths:
            diff_command.extend(["--", *paths])
        try:
            diff_run = subprocess.run(
                diff_command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=20,
                check=False,
            )
            names_run = subprocess.run(
                ["git", "-C", str(root), "diff", "--name-only"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return {
                "available": False,
                "status": "unavailable",
                "changed_files": [],
                "diff": "",
                "diff_excerpt": [],
            }
        if diff_run.returncode != 0 and "not a git repository" in (diff_run.stderr or "").lower():
            return {
                "available": False,
                "status": "not_git_repo",
                "changed_files": [],
                "diff": "",
                "diff_excerpt": [],
            }
        diff_text = diff_run.stdout.strip()
        changed_files = [line.strip() for line in names_run.stdout.splitlines() if line.strip()]
        excerpt = diff_text.splitlines()[:60]
        return {
            "available": True,
            "status": "captured" if diff_text else "empty",
            "changed_files": changed_files[:24],
            "diff": diff_text,
            "diff_excerpt": excerpt,
        }

    @staticmethod
    def _workspace_snapshot(root: Path, matches: list[RepoFileMatch], patch_snapshot: dict[str, Any]) -> dict[str, Any]:
        changed_files = patch_snapshot.get("changed_files", []) if isinstance(patch_snapshot, dict) else []
        return {
            "root": str(root),
            "candidate_count": len(matches),
            "candidate_paths": [item.path for item in matches[:6]],
            "git_available": bool(patch_snapshot.get("available", False)),
            "git_status": str(patch_snapshot.get("status", "")),
            "changed_files": changed_files[:12],
        }

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
    def _patch_artifact(
        query: str,
        matches: list[RepoFileMatch],
        tests: list[str],
        patch_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
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
        snapshot_status = str(patch_snapshot.get("status", "empty"))
        status = "captured" if snapshot_status == "captured" else ("draft" if file_plans else "empty")
        return {
            "status": status,
            "file_plans": file_plans,
            "targeted_test_files": tests[:3],
            "snapshot": {
                "kind": "git_diff" if bool(patch_snapshot.get("available", False)) else "synthetic",
                "status": snapshot_status,
                "changed_files": list(patch_snapshot.get("changed_files", []))[:12],
                "diff_excerpt": list(patch_snapshot.get("diff_excerpt", []))[:40],
            },
            "patch_stub": "*** Begin Patch\n" + "\n".join(diff_lines) + ("\n*** End Patch" if diff_lines else "\n*** End Patch"),
        }

    @staticmethod
    def _validation_report(
        commands: list[str],
        tests: list[str],
        matches: list[RepoFileMatch],
        trace: list[dict[str, Any]],
        evidence: dict[str, Any],
        executions: list[dict[str, Any]],
        execute_validation: bool,
    ) -> dict[str, Any]:
        blockers: list[str] = []
        if not matches:
            blockers.append("No candidate source files were found for this query.")
        if not commands:
            blockers.append("No project-level validation command could be inferred.")
        if execute_validation and commands and not executions:
            blockers.append("Validation execution was requested but no command run completed.")
        failure_clusters = CodeMissionPackBuilder._classify_validation_failures(executions)
        execution_summary = {
            "requested": execute_validation,
            "executed": len(executions),
            "passed": sum(1 for item in executions if item.get("status") == "passed"),
            "failed": sum(1 for item in executions if item.get("status") == "failed"),
            "timeouts": sum(1 for item in executions if item.get("status") == "timed_out"),
        }
        status = "ready"
        if blockers:
            status = "needs_review"
        elif execute_validation and execution_summary["failed"]:
            status = "failed"
        return {
            "status": status,
            "checks": [
                "candidate source files identified",
                "targeted or project-level validation command inferred",
                "execution trace captured",
                "evidence packet attached where available",
            ],
            "blockers": blockers,
            "execution_summary": execution_summary,
            "executions": executions,
            "failure_clusters": failure_clusters,
            "evidence_support": {
                "record_count": int(evidence.get("record_count", 0)),
                "citation_count": int(evidence.get("citation_count", 0)),
            },
            "trace_depth": len(trace),
            "targeted_tests": len(tests),
        }

    @staticmethod
    def _run_validation_commands(
        root: Path,
        commands: list[str],
        enabled: bool,
        timeout_seconds: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        if not enabled:
            return []
        rows: list[dict[str, Any]] = []
        for command in commands[: max(1, limit)]:
            start = time.perf_counter()
            try:
                result = subprocess.run(
                    command,
                    cwd=root,
                    shell=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    timeout=max(5, timeout_seconds),
                    check=False,
                )
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                stdout_lines = [line for line in result.stdout.splitlines() if line.strip()]
                stderr_lines = [line for line in result.stderr.splitlines() if line.strip()]
                rows.append(
                    {
                        "command": command,
                        "status": "passed" if result.returncode == 0 else "failed",
                        "exit_code": int(result.returncode),
                        "duration_ms": round(elapsed_ms, 2),
                        "stdout_tail": stdout_lines[-20:],
                        "stderr_tail": stderr_lines[-20:],
                    }
                )
            except subprocess.TimeoutExpired as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                stdout = str(exc.stdout or "")
                stderr = str(exc.stderr or "")
                rows.append(
                    {
                        "command": command,
                        "status": "timed_out",
                        "exit_code": -1,
                        "duration_ms": round(elapsed_ms, 2),
                        "stdout_tail": [line for line in stdout.splitlines() if line.strip()][-20:],
                        "stderr_tail": [line for line in stderr.splitlines() if line.strip()][-20:],
                    }
                )
        return rows

    @staticmethod
    def _classify_validation_failures(executions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counters: dict[str, int] = {}
        for row in executions:
            status = str(row.get("status", ""))
            stderr = "\n".join(row.get("stderr_tail", []))
            stdout = "\n".join(row.get("stdout_tail", []))
            if status == "timed_out":
                counters["timeout"] = counters.get("timeout", 0) + 1
                continue
            if status != "failed":
                continue
            label = "command_failed"
            blob = f"{stdout}\n{stderr}".lower()
            if "error collecting" in blob:
                label = "collection_error"
            elif "assert" in blob or "failed" in blob:
                label = "test_failure"
            elif "modulenotfounderror" in blob or "importerror" in blob:
                label = "import_error"
            counters[label] = counters.get(label, 0) + 1
        return [{"name": key, "count": value} for key, value in sorted(counters.items(), key=lambda item: item[1], reverse=True)]

    @staticmethod
    def _task_graph(
        query: str,
        matches: list[RepoFileMatch],
        tests: list[str],
        commands: list[str],
        trace: list[dict[str, Any]],
        patch: dict[str, Any],
        validation: dict[str, Any],
        workspace_snapshot: dict[str, Any],
        execute_validation: bool,
    ) -> dict[str, Any]:
        validation_summary = validation.get("execution_summary", {}) if isinstance(validation, dict) else {}
        nodes = [
            TaskGraphNode(
                node_id="scope_workspace",
                title="Scope candidate files",
                node_type="analysis",
                status="completed" if matches else "blocked",
                notes=[
                    f"candidate files: {len(matches)}",
                    f"git status: {workspace_snapshot.get('git_status', '')}",
                ],
                artifacts=[
                    TaskGraphArtifact(
                        kind="workspace_snapshot",
                        label="Workspace snapshot",
                        status="completed" if matches else "blocked",
                        path=str(workspace_snapshot.get("root", "")),
                        summary=", ".join(workspace_snapshot.get("candidate_paths", [])[:3]),
                    )
                ],
                metrics={"candidate_count": len(matches)},
            ),
            TaskGraphNode(
                node_id="capture_patch",
                title="Capture patch artifact",
                node_type="artifact",
                status="completed" if patch.get("status") in {"captured", "draft"} else "blocked",
                depends_on=["scope_workspace"],
                notes=[f"patch status: {patch.get('status', '')}"],
                artifacts=[
                    TaskGraphArtifact(
                        kind="patch",
                        label="Patch artifact",
                        status="completed" if patch.get("status") in {"captured", "draft"} else "blocked",
                        summary=f"{len(patch.get('file_plans', []))} planned files",
                    )
                ],
                metrics={"planned_files": len(patch.get("file_plans", []))},
            ),
            TaskGraphNode(
                node_id="target_tests",
                title="Infer targeted validation",
                node_type="validation_plan",
                status="completed" if commands else "blocked",
                depends_on=["capture_patch"],
                commands=list(commands[:3]),
                notes=[f"targeted tests: {len(tests)}"],
                artifacts=[
                    TaskGraphArtifact(
                        kind="test_plan",
                        label="Validation commands",
                        status="completed" if commands else "blocked",
                        summary=", ".join(commands[:2]),
                    )
                ],
                metrics={"targeted_tests": len(tests), "command_count": len(commands)},
            ),
            TaskGraphNode(
                node_id="run_validation",
                title="Run validation commands",
                node_type="execution",
                status=(
                    "completed"
                    if execute_validation and validation_summary.get("executed", 0) > 0 and validation_summary.get("failed", 0) == 0
                    else "failed"
                    if execute_validation and validation_summary.get("failed", 0) > 0
                    else "ready"
                    if commands
                    else "blocked"
                ),
                depends_on=["target_tests"],
                commands=list(commands[:3]),
                notes=[
                    "validation executed" if execute_validation else "validation execution deferred",
                    f"trace depth: {len(trace)}",
                ],
                artifacts=[
                    TaskGraphArtifact(
                        kind="validation_execution",
                        label="Validation execution",
                        status=(
                            "completed"
                            if execute_validation and validation_summary.get("executed", 0) > 0
                            else "ready"
                            if commands
                            else "blocked"
                        ),
                        summary=f"executed={validation_summary.get('executed', 0)} passed={validation_summary.get('passed', 0)}",
                    )
                ],
                metrics=dict(validation_summary),
            ),
            TaskGraphNode(
                node_id="publish_report",
                title="Publish validation artifact",
                node_type="report",
                status="completed" if validation.get("status") in {"ready", "failed"} else "blocked",
                depends_on=["run_validation"],
                notes=[
                    f"report status: {validation.get('status', '')}",
                    f"failure clusters: {len(validation.get('failure_clusters', []))}",
                ],
                artifacts=[
                    TaskGraphArtifact(
                        kind="validation_report",
                        label="Validation report",
                        status="completed" if validation.get("status") in {"ready", "failed"} else "blocked",
                        summary=f"blockers={len(validation.get('blockers', []))}",
                    )
                ],
                metrics={
                    "trace_depth": len(trace),
                    "blocker_count": len(validation.get("blockers", [])),
                },
            ),
        ]
        graph = ExecutableTaskGraph(
            graph_id="code-mission-graph",
            mission_type="code_mission_pack",
            query=query,
            nodes=nodes,
        )
        return graph.to_dict()
