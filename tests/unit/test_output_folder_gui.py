from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from find_that_text.gui import main_window


def test_output_folder_choice_is_remembered_and_can_be_reset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    settings_path = tmp_path / "settings.ini"
    monkeypatch.setattr(
        main_window,
        "QSettings",
        lambda *_: QSettings(str(settings_path), QSettings.Format.IniFormat),
    )
    default_root = tmp_path / "Downloads" / "Find That Text Reports"
    monkeypatch.setattr(main_window, "default_reports_root", lambda: default_root)
    custom_root = tmp_path / "Project Reports"
    custom_root.mkdir()
    monkeypatch.setattr(
        main_window.QFileDialog,
        "getExistingDirectory",
        lambda *_: str(custom_root),
    )

    first = main_window.MainWindow()
    assert first.output_root == default_root
    first.choose_output_root()
    assert first.output_root == custom_root
    assert first.output_path.text() == str(custom_root)

    second = main_window.MainWindow()
    assert second.output_root == custom_root
    second.reset_output_root()
    assert second.output_root == default_root
    assert second.output_path.text() == str(default_root)

    third = main_window.MainWindow()
    assert third.output_root == default_root
    for window in (first, second, third):
        window.close()
    del app
