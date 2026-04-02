"""Tests for skill interoperability export layer."""

from __future__ import annotations

import json
from pathlib import Path

from app.skills.interop import export_interop_all, export_interop_catalog, write_interop_bundle


def test_export_interop_catalog_openai_shape() -> None:
    payload = export_interop_catalog(
        framework="openai",
        include_marketplace=False,
        include_external=False,
        include_harness_tools=True,
    )
    assert payload["framework"] == "openai"
    assert payload["skill_count"] > 0
    first = payload["skills"][0]
    assert "_" not in first["name"]
    assert first["name"] == first["name"].lower()
    assert first["metadata"]["framework_target"] == "openai"
    assert "skill_md" in first
    assert first["skill_md"].startswith("---")
    assert "allowed-tools:" in first["skill_md"]


def test_export_interop_catalog_anthropic_metadata() -> None:
    payload = export_interop_catalog(
        framework="anthropic",
        include_marketplace=False,
        include_external=False,
        include_harness_tools=False,
    )
    assert payload["framework"] == "anthropic"
    first = payload["skills"][0]
    assert first["metadata"]["framework_target"] == "anthropic"
    assert first["allowed_tools"] == []


def test_write_interop_bundle_for_all_frameworks(tmp_path: Path) -> None:
    payload = export_interop_all(
        include_marketplace=False,
        include_external=False,
        include_harness_tools=False,
    )
    result = write_interop_bundle(payload, output_dir=tmp_path / "interop")
    assert Path(result["index"]).exists()
    assert "frameworks" in result

    openai = result["frameworks"]["openai"]
    anth = result["frameworks"]["anthropic"]
    assert Path(openai["index"]).exists()
    assert Path(anth["index"]).exists()

    openai_index = json.loads(Path(openai["index"]).read_text(encoding="utf-8"))
    assert openai_index["framework"] == "openai"
    assert openai_index["skill_count"] > 0

    first_path = Path(openai_index["skills"][0]["path"])
    assert first_path.exists()
    content = first_path.read_text(encoding="utf-8")
    assert content.startswith("---")
    assert "compatibility:" in content
