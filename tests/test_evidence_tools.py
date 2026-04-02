"""Tests for evidence injection tools and summaries."""

from __future__ import annotations

from app.harness.models import ToolCall, ToolType
from app.harness.tools import ToolRegistry


def test_evidence_dossier_builder_returns_normalized_records() -> None:
    registry = ToolRegistry()
    result = registry.call(
        ToolCall(
            name="evidence_dossier_builder",
            tool_type=ToolType.BROWSER,
            args={"query": "regulated fintech audit controls for customer support copilot", "limit": 4},
        )
    )

    assert result.success is True
    assert result.output["record_count"] >= 1
    assert len(result.metadata.get("evidence_records", [])) >= 1
    assert len(result.metadata.get("evidence_citations", [])) >= 1


def test_policy_risk_matrix_uses_evidence_packet() -> None:
    registry = ToolRegistry()
    result = registry.call(
        ToolCall(
            name="policy_risk_matrix",
            tool_type=ToolType.CODE,
            args={"query": "audit governance controls for fintech support agent", "evidence_limit": 4},
        )
    )

    assert result.success is True
    assert result.output["evidence_packet"]["count"] >= 1
    assert len(result.metadata.get("evidence_records", [])) >= 1
