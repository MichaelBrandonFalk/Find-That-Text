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
    report_file = tmp_path / "shareable_report.html"
    report_file.write_text("<html>Standalone report</html>", encoding="utf-8")
    exported_file = tmp_path / "coworker-report.html"
    monkeypatch.setattr(
        main_window.QFileDialog,
        "getSaveFileName",
        lambda *_: (str(exported_file), "HTML Files (*.html)"),
    )
    third.output_dir = tmp_path / "scan-results"
    third.shareable_report_path = report_file
    third.export_shareable_report()
    assert exported_file.read_text(encoding="utf-8") == "<html>Standalone report</html>"
    opened_urls = []
    monkeypatch.setattr(main_window.QDesktopServices, "openUrl", opened_urls.append)
    third.report_path = report_file
    third.open_report()
    assert Path(opened_urls[0].toLocalFile()) == report_file
    assert "GitHub Repo" in " ".join(label.text() for label in third.statusBar().findChildren(main_window.QLabel))
    for window in (first, second, third):
        window.close()
    del app
