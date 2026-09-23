from __future__ import annotations

from pathlib import Path

from find_that_text.util.paths import create_output_dir, default_reports_root


def test_reports_default_to_downloads(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    expected_root = tmp_path / "Downloads" / "Find That Text Reports"
    assert default_reports_root() == expected_root

    output_dir = create_output_dir("feature.mov")
    assert output_dir.parent == expected_root
    assert (output_dir / "screenshots").is_dir()


def test_custom_report_root_is_used(tmp_path: Path) -> None:
    custom_root = tmp_path / "Selected Reports"

    output_dir = create_output_dir("feature.mov", custom_root)

    assert output_dir.parent == custom_root
    assert (output_dir / "screenshots").is_dir()
