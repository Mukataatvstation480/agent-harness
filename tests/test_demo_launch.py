"""Tests for launch demo asset generation."""

from __future__ import annotations

from pathlib import Path

from app.demo import demo_press_launch


def test_demo_press_launch_writes_assets(tmp_path: Path) -> None:
    payload = demo_press_launch(output_dir=str(tmp_path), tag="unit")
    paths = payload.get("paths", {})

    assert "identity" in payload
    assert Path(str(paths.get("json", ""))).exists()
    assert Path(str(paths.get("html", ""))).exists()
    assert Path(str(paths.get("brief", ""))).exists()
    assert Path(str(paths.get("manifest", ""))).exists()
    assert Path(str(paths.get("interop", {}).get("index", ""))).exists()
