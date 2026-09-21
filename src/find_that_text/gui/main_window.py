from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from find_that_text.scanner import ScanCancelled, ScanProgress, ScanSettings, scan_video
from find_that_text.util.paths import default_reports_root
from find_that_text.util.timestamps import format_timestamp, parse_timestamp
from find_that_text.version import __version__


class DropFrame(QFrame):
    fileDropped = Signal(Path)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropFrame")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Drop a video here")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("dropTitle")
        subtitle = QLabel("or choose a MOV, MP4, or M4V")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(subtitle)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in {".mov", ".mp4", ".m4v"}:
                self.fileDropped.emit(path)
                break


class ScanThread(QThread):
    progressChanged = Signal(object)
    scanFinished = Signal(object)
    scanFailed = Signal(str)
    scanCancelled = Signal()

    def __init__(self, video_path: Path, settings: ScanSettings) -> None:
        super().__init__()
        self.video_path = video_path
        self.settings = settings
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        try:
            result = scan_video(
                self.video_path,
                settings=self.settings,
                progress_callback=lambda progress: self.progressChanged.emit(progress),
                cancel_event=self.cancel_event,
            )
        except ScanCancelled:
            self.scanCancelled.emit()
        except Exception as exc:  # pragma: no cover - GUI surface
            self.scanFailed.emit(str(exc))
        else:
            self.scanFinished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Find That Text")
        self.resize(720, 520)
        self.video_path: Path | None = None
        self.output_dir: Path | None = None
        self.thread: ScanThread | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        header = QHBoxLayout()
        title = QLabel("Find That Text")
        title.setObjectName("appTitle")
        version = QLabel(f"Version {__version__}")
        version.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(title, 1)
        header.addWidget(version)
        layout.addLayout(header)

        self.drop_frame = DropFrame()
        self.drop_frame.fileDropped.connect(self.set_video_path)
        layout.addWidget(self.drop_frame)

        choose_row = QHBoxLayout()
        self.file_label = QLabel("No video selected")
        self.choose_button = QPushButton("Choose Video")
        self.choose_button.clicked.connect(self.choose_video)
        choose_row.addWidget(self.file_label, 1)
        choose_row.addWidget(self.choose_button)
        layout.addLayout(choose_row)

        form = QGridLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Default", "default")
        self.mode_combo.addItem("Advanced", "advanced")
        self.start_time_input = QLineEdit()
        self.start_time_input.setPlaceholderText("00:00:00")
        self.end_time_input = QLineEdit()
        self.end_time_input.setPlaceholderText("Full video")
        self.annotated_check = QCheckBox("Save annotated screenshots")
        self.output_label = QLabel(str(default_reports_root()))
        form.addWidget(QLabel("Scan Mode"), 0, 0)
        form.addWidget(self.mode_combo, 0, 1)
        form.addWidget(QLabel("Start"), 1, 0)
        form.addWidget(self.start_time_input, 1, 1)
        form.addWidget(QLabel("End"), 2, 0)
        form.addWidget(self.end_time_input, 2, 1)
        form.addWidget(self.annotated_check, 3, 1)
        form.addWidget(QLabel("Output"), 4, 0)
        form.addWidget(self.output_label, 4, 1)
        layout.addLayout(form)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.scan_button = QPushButton("Scan Video")
        self.scan_button.clicked.connect(self.start_scan)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_scan)
        self.open_output_button = QPushButton("Open Output Folder")
        self.open_output_button.setEnabled(False)
        self.open_output_button.clicked.connect(self.open_output_folder)
        buttons.addWidget(self.open_output_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.scan_button)
        layout.addLayout(buttons)

        self.setStyleSheet(
            """
            #appTitle { font-size: 28px; font-weight: 700; }
            #dropFrame {
                border: 2px dashed #9aa3ad;
                border-radius: 8px;
                min-height: 168px;
                background: rgba(120, 130, 140, 0.08);
            }
            #dropTitle { font-size: 22px; font-weight: 600; }
            QPushButton { padding: 7px 14px; }
            """
        )

    def choose_video(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose Video",
            str(Path.home()),
            "Video Files (*.mov *.mp4 *.m4v)",
        )
        if filename:
            self.set_video_path(Path(filename))

    def set_video_path(self, path: Path) -> None:
        self.video_path = path
        self.file_label.setText(path.name)
        self.status_label.setText("Ready to scan")

    def start_scan(self) -> None:
        if self.video_path is None:
            QMessageBox.information(self, "Choose a video", "Choose or drop a video before scanning.")
            return
        try:
            start_seconds = self._optional_timestamp(self.start_time_input.text())
            end_seconds = self._optional_timestamp(self.end_time_input.text())
        except ValueError as exc:
            QMessageBox.information(self, "Check timestamps", str(exc))
            return
        settings = ScanSettings(
            mode=str(self.mode_combo.currentData()),
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            save_annotated_screenshots=self.annotated_check.isChecked(),
        )
        self.thread = ScanThread(self.video_path, settings)
        self.thread.progressChanged.connect(self.update_progress)
        self.thread.scanFinished.connect(self.scan_finished)
        self.thread.scanFailed.connect(self.scan_failed)
        self.thread.scanCancelled.connect(self.scan_cancelled)
        self.scan_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.open_output_button.setEnabled(False)
        self.progress.setValue(0)
        self.status_label.setText("Initializing OCR...")
        self.thread.start()

    def cancel_scan(self) -> None:
        if self.thread:
            self.thread.cancel()
            self.status_label.setText("Cancelling...")
            self.cancel_button.setEnabled(False)

    def update_progress(self, progress: ScanProgress) -> None:
        self.progress.setValue(int(progress.fraction * 1000))
        self.status_label.setText(
            f"{progress.filename} - {format_timestamp(progress.current_seconds)} / "
            f"{format_timestamp(progress.scan_end_seconds)} - "
            f"{progress.detections_found} detections"
        )

    def scan_finished(self, result: object) -> None:
        self.output_dir = result.output_dir
        self.progress.setValue(1000)
        self.status_label.setText(f"Complete - {len(result.events)} text events detected")
        self.scan_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.open_output_button.setEnabled(True)

    def scan_failed(self, message: str) -> None:
        self.scan_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Scan failed")
        QMessageBox.critical(self, "Scan failed", message)

    def scan_cancelled(self) -> None:
        self.scan_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Scan cancelled")

    def open_output_folder(self) -> None:
        if self.output_dir:
            subprocess.run(["open", str(self.output_dir)], check=False)

    @staticmethod
    def _optional_timestamp(value: str) -> float | None:
        if not value.strip():
            return None
        return parse_timestamp(value)


def run(argv: list[str]) -> int:
    app = QApplication(argv)
    window = MainWindow()
    window.show()
    return app.exec()
