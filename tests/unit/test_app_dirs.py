from __future__ import annotations

from pathlib import Path

from find_that_text.util import app_dirs


def test_windows_app_support_uses_local_app_data(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_dirs.platform, "system", lambda: "Windows")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("FIND_THAT_TEXT_APP_SUPPORT", raising=False)

    assert app_dirs.app_support_dir() == tmp_path / "Find That Text"


def test_frozen_windows_models_are_read_from_bundle(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_dirs.platform, "system", lambda: "Windows")
    monkeypatch.setattr(app_dirs.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app_dirs.sys, "_MEIPASS", str(tmp_path), raising=False)

    assert app_dirs.bundled_paddlex_dir() == tmp_path / "PaddleX"
