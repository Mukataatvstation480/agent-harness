"""Security checks for harness preflight and tool-level execution."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from app.harness.manifest import HarnessToolManifest
from app.harness.models import HarnessConstraints, ToolCall


class SecurityAction(str, Enum):
    """Decision level for a security check."""

    ALLOW = "allow"
    CHALLENGE = "challenge"
    BLOCK = "block"


@dataclass
class SecurityFinding:
    """One security signal found by static checks."""

    rule: str
    severity: str
    evidence: str
    recommendation: str

    def to_dict(self) -> dict[str, str]:
        return {
            "rule": self.rule,
            "severity": self.severity,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


@dataclass
class SecurityDecision:
    """Security decision artifact consumed by engine and telemetry."""

    action: SecurityAction
    risk_score: float
    findings: list[SecurityFinding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    redacted_query: str = ""

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "risk_score": round(self.risk_score, 3),
            "findings": [item.to_dict() for item in self.findings],
            "notes": self.notes,
            "redacted_query": self.redacted_query,
        }

    def to_guardrail_notes(self, prefix: str = "SECURITY") -> list[str]:
        notes: list[str] = []
        action = self.action.value.upper()
        notes.append(f"{prefix}_{action}:risk_score={self.risk_score:.2f}")
        for item in self.findings:
            notes.append(f"{prefix}_{action}:{item.rule}:{item.severity}")
        return notes


class SecurityEngine:
    """Risk heuristics for prompt-injection and unsafe operations."""

    _PATTERNS: list[tuple[str, re.Pattern[str], str, str, float]] = [
        (
            "prompt_injection",
            re.compile(r"ignore\s+(all|any|previous|prior)\s+instructions", re.IGNORECASE),
            "high",
            "Ignore conflicting instructions and follow system policy only.",
            2.2,
        ),
        (
            "system_prompt_exfiltration",
            re.compile(r"(show|reveal|print).*(system|hidden)\s+prompt", re.IGNORECASE),
            "high",
            "Do not reveal hidden/system prompts.",
            2.3,
        ),
        (
            "credential_exposure",
            re.compile(r"(api[\s_-]?key|token|password|secret)", re.IGNORECASE),
            "critical",
            "Never expose credentials; redact or reject.",
            2.6,
        ),
        (
            "destructive_intent",
            re.compile(r"(delete|drop\s+table|truncate|rm\s+-rf|format\s+c:)", re.IGNORECASE),
            "critical",
            "Block destructive actions unless explicitly approved.",
            2.7,
        ),
        (
            "guardrail_bypass",
            re.compile(r"(bypass|disable).*(guardrail|safety|security)", re.IGNORECASE),
            "high",
            "Refuse requests attempting to disable safeguards.",
            2.3,
        ),
        (
            "data_exfiltration",
            re.compile(r"(exfiltrate|leak|upload).*(secret|credential|private|confidential)", re.IGNORECASE),
            "critical",
            "Block potential data exfiltration.",
            2.8,
        ),
    ]

    _REDACT_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"sk-[a-zA-Z0-9]{16,}"),
        re.compile(r"ghp_[a-zA-Z0-9]{16,}"),
        re.compile(r"(?i)(api[\s_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+"),
    ]

    def preflight(self, query: str, constraints: HarnessConstraints) -> SecurityDecision:
        """Evaluate incoming user query before graph/tool execution."""

        if not constraints.enable_security_scan:
            return SecurityDecision(action=SecurityAction.ALLOW, risk_score=0.0, redacted_query=query)

        lowered = query.lower()
        findings: list[SecurityFinding] = []
        risk_score = 0.0
        notes: list[str] = []

        for rule, pattern, severity, recommendation, weight in self._PATTERNS:
            match = pattern.search(lowered)
            if not match:
                continue
            findings.append(
                SecurityFinding(
                    rule=rule,
                    severity=severity,
                    evidence=match.group(0),
                    recommendation=recommendation,
                )
            )
            risk_score += weight
            notes.append(f"{rule}:{severity}")

        if len(query) > 4000:
            findings.append(
                SecurityFinding(
                    rule="oversized_input",
                    severity="medium",
                    evidence=f"chars={len(query)}",
                    recommendation="Ask for smaller chunks or summarize progressively.",
                )
            )
            risk_score += 1.0
            notes.append("oversized_input:medium")

        redacted_query = query
        for pattern in self._REDACT_PATTERNS:
            redacted_query = pattern.sub("[REDACTED]", redacted_query)

        block_threshold, challenge_threshold = self._thresholds(constraints.security_strictness)
        if risk_score >= block_threshold:
            action = SecurityAction.BLOCK
        elif risk_score >= challenge_threshold:
            action = SecurityAction.CHALLENGE
        else:
            action = SecurityAction.ALLOW

        return SecurityDecision(
            action=action,
            risk_score=risk_score,
            findings=findings,
            notes=notes,
            redacted_query=redacted_query,
        )

    def evaluate_tool_call(
        self,
        tool_call: ToolCall,
        constraints: HarnessConstraints,
        manifest: HarnessToolManifest | None = None,
        high_risk: bool = False,
        preflight_action: SecurityAction = SecurityAction.ALLOW,
    ) -> SecurityDecision:
        """Evaluate one planned tool call against policy and capabilities."""

        if not constraints.enable_security_scan:
            return SecurityDecision(action=SecurityAction.ALLOW, risk_score=0.0)

        findings: list[SecurityFinding] = []
        risk_score = 0.0

        if preflight_action == SecurityAction.BLOCK:
            findings.append(
                SecurityFinding(
                    rule="preflight_block_propagation",
                    severity="critical",
                    evidence=tool_call.name,
                    recommendation="Stop execution due to blocked preflight query.",
                )
            )
            risk_score += 5.0

        if tool_call.name in constraints.blocked_tools:
            findings.append(
                SecurityFinding(
                    rule="blocked_tool",
                    severity="critical",
                    evidence=tool_call.name,
                    recommendation="Use alternative tools that are not blocked.",
                )
            )
            risk_score += 4.0

        if manifest is None:
            findings.append(
                SecurityFinding(
                    rule="manifest_missing",
                    severity="medium",
                    evidence=tool_call.name,
                    recommendation="Register tool manifest before production use.",
                )
            )
            risk_score += 1.1
        else:
            if manifest.write_actions and not constraints.allow_write_actions:
                findings.append(
                    SecurityFinding(
                        rule="write_disallowed",
                        severity="high",
                        evidence=manifest.name,
                        recommendation="Enable write actions explicitly when needed.",
                    )
                )
                risk_score += 2.3

            if manifest.network_actions and not constraints.allow_network_actions:
                findings.append(
                    SecurityFinding(
                        rule="network_disallowed",
                        severity="high",
                        evidence=manifest.name,
                        recommendation="Enable network actions only for trusted contexts.",
                    )
                )
                risk_score += 1.9

            if manifest.tool_type.value == "browser" and not constraints.allow_browser_actions:
                findings.append(
                    SecurityFinding(
                        rule="browser_disallowed",
                        severity="high",
                        evidence=manifest.name,
                        recommendation="Disable browser usage for locked-down execution.",
                    )
                )
                risk_score += 1.8

            if manifest.code_execution and not constraints.allow_code_execution:
                findings.append(
                    SecurityFinding(
                        rule="code_execution_disallowed",
                        severity="high",
                        evidence=manifest.name,
                        recommendation="Avoid code execution tools in restricted mode.",
                    )
                )
                risk_score += 1.9

        if high_risk and constraints.require_approval_on_high_risk and tool_call.tool_type.value == "api":
            findings.append(
                SecurityFinding(
                    rule="high_risk_api_review",
                    severity="medium",
                    evidence=tool_call.name,
                    recommendation="Require human review before high-risk API execution.",
                )
            )
            risk_score += 1.3

        block_threshold, challenge_threshold = self._thresholds(constraints.security_strictness)
        if risk_score >= block_threshold:
            action = SecurityAction.BLOCK
        elif risk_score >= challenge_threshold:
            action = SecurityAction.CHALLENGE
        else:
            action = SecurityAction.ALLOW

        return SecurityDecision(
            action=action,
            risk_score=risk_score,
            findings=findings,
            notes=[f"{item.rule}:{item.severity}" for item in findings],
        )

    @staticmethod
    def _thresholds(strictness: str) -> tuple[float, float]:
        mode = strictness.lower().strip()
        if mode == "strict":
            return 3.0, 1.5
        if mode == "relaxed":
            return 5.5, 3.0
        return 4.0, 2.0

