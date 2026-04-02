"""Tests for baseline generation helpers."""

from app.harness.ci_baseline import _parse_presets


def test_parse_presets_defaults_and_values() -> None:
    assert _parse_presets("") == ["core", "daily", "research", "strict"]
    assert _parse_presets("core, strict") == ["core", "strict"]
