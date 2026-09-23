from __future__ import annotations

import subprocess
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from find_that_text.captions import find_sidecar_caption
from find_that_text.ocr.engine import PaddleOCREngine
from find_that_text.scanner import (
    DialogueGapResult,
    ScanCancelled,
    ScanProgress,
    ScanSettings,
    find_dialogue_gaps,
    scan_video,
)
from find_that_text.tracking.relevance import LIKELY_FORCED_TEXT, NEEDS_REVIEW, bucket_counts
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
            if self.settings.gaps_only:
                result = find_dialogue_gaps(self.video_path, settings=self.settings)
            else:
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
        self.resize(780, 820)
        self.video_path: Path | None = None
        self.caption_path: Path | None = None
        self.auto_find_captions = True
        self.output_dir: Path | None = None
        self.report_path: Path | None = None
        self.thread: ScanThread | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer_layout = QVBoxLayout(root)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        scroll = QScrollArea()
        self.scroll_area = scroll
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        content = QWidget()
        scroll.setWidget(content)
        outer_layout.addWidget(scroll, 1)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

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

        caption_group = QGroupBox("Dialogue Captions")
        caption_layout = QVBoxLayout(caption_group)
        caption_row = QHBoxLayout()
        self.caption_label = QLabel("No SRT or VTT selected")
        self.caption_label.setObjectName("captionLabel")
        self.caption_button = QPushButton("Choose SRT/VTT")
        self.caption_button.clicked.connect(self.choose_caption)
        self.clear_caption_button = QPushButton("Clear")
        self.clear_caption_button.clicked.connect(self.clear_caption)
        caption_row.addWidget(self.caption_label, 1)
        caption_row.addWidget(self.caption_button)
        caption_row.addWidget(self.clear_caption_button)
        caption_layout.addLayout(caption_row)
        self.gap_only_check = QCheckBox("Scan only where dialogue captions are absent")
        self.gap_only_check.setChecked(True)
        self.gap_only_check.setToolTip("Fastest with SRT/VTT captions; text shown during dialogue may be missed.")
        caption_layout.addWidget(self.gap_only_check)
        gap_row = QHBoxLayout()
        gap_row.addWidget(QLabel("Minimum dialogue-free break"))
        self.minimum_gap_slider = QSlider(Qt.Orientation.Horizontal)
        self.minimum_gap_slider.setRange(0, 50)
        self.minimum_gap_slider.setValue(10)
        self.minimum_gap_slider.setTickInterval(5)
        self.minimum_gap_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.minimum_gap_slider.setToolTip("Only scan caption-free breaks at least this long, before speech margins.")
        gap_row.addWidget(self.minimum_gap_slider, 1)
        self.minimum_gap_value = QLabel("1.0 s")
        self.minimum_gap_value.setMinimumWidth(42)
        gap_row.addWidget(self.minimum_gap_value)
        caption_layout.addLayout(gap_row)
        layout.addWidget(caption_group)

        run_row = QHBoxLayout()
        self.run_combo = QComboBox()
        self.run_combo.addItem("Screen-text scan", False)
        self.run_combo.addItem("Super Speed Run - dialogue gaps only", True)
        self.run_combo.setItemData(
            1,
            "Exports dialogue-free timecodes from SRT/VTT captions. No video frames or OCR are processed.",
            Qt.ItemDataRole.ToolTipRole,
        )
        run_row.addWidget(QLabel("Run"))
        run_row.addWidget(self.run_combo, 1)
        layout.addLayout(run_row)

        range_form = QGridLayout()
        self.start_time_input = QLineEdit()
        self.start_time_input.setPlaceholderText("00:00:00")
        self.end_time_input = QLineEdit()
        self.end_time_input.setPlaceholderText("Full video")
        range_form.addWidget(QLabel("Start"), 0, 0)
        range_form.addWidget(self.start_time_input, 0, 1)
        range_form.addWidget(QLabel("End"), 1, 0)
        range_form.addWidget(self.end_time_input, 1, 1)
        layout.addLayout(range_form)

        self.advanced_toggle = QPushButton("Show Advanced Settings")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.toggled.connect(self._toggle_advanced)
        layout.addWidget(self.advanced_toggle)

        self.advanced_group = QGroupBox("Advanced Settings")
        advanced_form = QGridLayout(self.advanced_group)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Fastest - every 23 frames", "default")
        self.mode_combo.addItem("Adaptive - closer checks in gaps", "adaptive")
        self.mode_combo.addItem("Every frame", "advanced")
        self.mode_combo.addItem("Custom frame interval", "custom")
        advanced_form.addWidget(QLabel("Scan Mode"), 0, 0)
        advanced_form.addWidget(self.mode_combo, 0, 1)

        self.custom_frame_step = QSpinBox()
        self.custom_frame_step.setRange(1, 100_000)
        self.custom_frame_step.setValue(23)
        self.custom_frame_step.setSuffix(" frames")
        advanced_form.addWidget(QLabel("Frame Interval"), 1, 0)
        advanced_form.addWidget(self.custom_frame_step, 1, 1)

        self.breadth_slider = QSlider(Qt.Orientation.Horizontal)
        self.breadth_slider.setRange(0, 100)
        self.breadth_slider.setValue(50)
        self.breadth_slider.setTickInterval(10)
        self.breadth_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        breadth_row = QHBoxLayout()
        breadth_row.addWidget(QLabel("Show more"))
        breadth_row.addWidget(self.breadth_slider, 1)
        breadth_row.addWidget(QLabel("Clear results"))
        self.breadth_value = QLabel()
        advanced_form.addWidget(QLabel("Review Breadth"), 2, 0)
        advanced_form.addLayout(breadth_row, 2, 1)
        advanced_form.addWidget(self.breadth_value, 3, 1)

        self.scene_detection_check = QCheckBox("Use scene-change detection")
        self.scene_detection_check.setChecked(False)
        self.scene_detection_check.setToolTip("Adds a full-video scene pass before OCR; useful for brief text at cuts.")
        self.reuse_check = QCheckBox("Reuse OCR on near-identical frames")
        self.reuse_check.setChecked(True)
        self.reuse_check.setToolTip("Skips repeat OCR only when sampled frames barely change; every third frame is refreshed.")
        self.annotated_check = QCheckBox("Save annotated screenshots")
        advanced_form.addWidget(self.scene_detection_check, 4, 1)
        advanced_form.addWidget(self.reuse_check, 5, 1)
        advanced_form.addWidget(self.annotated_check, 6, 1)
        advanced_form.addWidget(QLabel("Output"), 7, 0)
        self.output_label = QLabel(str(default_reports_root()))
        advanced_form.addWidget(self.output_label, 7, 1)
        self.advanced_group.setVisible(False)
        layout.addWidget(self.advanced_group)

        self.mode_combo.currentIndexChanged.connect(self._sync_scan_mode_controls)
        self.run_combo.currentIndexChanged.connect(self._sync_run_controls)
        self.breadth_slider.valueChanged.connect(self._update_breadth_label)
        self.minimum_gap_slider.valueChanged.connect(self._update_minimum_gap_label)
        self.gap_only_check.toggled.connect(self._sync_caption_controls)
        self._sync_scan_mode_controls()
        self._sync_caption_controls()
        self._update_breadth_label(self.breadth_slider.value())
        self._update_minimum_gap_label(self.minimum_gap_slider.value())

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.status_label = QLabel("Ready")
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(28, 12, 28, 16)
        controls_layout.setSpacing(12)
        controls_layout.addWidget(self.status_label)
        controls_layout.addWidget(self.progress)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.scan_button = QPushButton("Scan Video")
        self.scan_button.clicked.connect(self.start_scan)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_scan)
        self.open_output_button = QPushButton("Open Report")
        self.open_output_button.setEnabled(False)
        self.open_output_button.clicked.connect(self.open_report)
        buttons.addWidget(self.open_output_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.scan_button)
        controls_layout.addLayout(buttons)
        outer_layout.addWidget(controls)
        self._sync_run_controls()

        technology_label = QLabel(
            'Video: <a href="https://ffmpeg.org/">FFmpeg</a> via '
            '<a href="https://github.com/PyAV-Org/PyAV">PyAV 18.1.0</a> | '
            'OCR: <a href="https://github.com/PaddlePaddle/PaddleOCR">'
            f'PaddleOCR {PaddleOCREngine.version}</a> '
            '(PP-OCRv6 small)<br>'
            'Optional scene detection: '
            '<a href="https://github.com/Breakthrough/PySceneDetect">PySceneDetect 0.7.1</a>'
        )
        technology_label.setObjectName("technologyCredits")
        technology_label.setOpenExternalLinks(True)
        technology_label.setTextFormat(Qt.TextFormat.RichText)
        self.statusBar().addWidget(technology_label, 1)

        self.setStyleSheet(
            """
            #appTitle { font-size: 28px; font-weight: 700; }
            #dropFrame {
                border: 2px dashed #9aa3ad;
                border-radius: 8px;
                min-height: 142px;
                background: rgba(120, 130, 140, 0.08);
            }
            #dropTitle { font-size: 22px; font-weight: 600; }
            #captionLabel { color: #526274; }
            #technologyCredits { color: #526274; font-size: 11px; }
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

    def choose_caption(self) -> None:
        start_dir = self.video_path.parent if self.video_path else Path.home()
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose English or Spanish Dialogue Captions",
            str(start_dir),
            "Caption Files (*.srt *.vtt)",
        )
        if filename:
            self.set_caption_path(Path(filename), auto_detected=False)

    def set_video_path(self, path: Path) -> None:
        self.video_path = path
        self.auto_find_captions = True
        self.file_label.setText(path.name)
        sidecar = find_sidecar_caption(path)
        if sidecar:
            self.set_caption_path(sidecar, auto_detected=True)
            self.status_label.setText("Ready - matching captions found")
        else:
            self.caption_path = None
            self.caption_label.setText("No SRT or VTT selected")
            self.status_label.setText("Ready - no captions; scanning all video at 23-frame intervals")
            self._sync_caption_controls()

    def set_caption_path(self, path: Path, *, auto_detected: bool) -> None:
        self.caption_path = path
        self.auto_find_captions = auto_detected
        suffix = " (automatic)" if auto_detected else ""
        self.caption_label.setText(f"{path.name}{suffix}")
        self._sync_caption_controls()

    def clear_caption(self) -> None:
        self.caption_path = None
        self.auto_find_captions = False
        self.caption_label.setText("No SRT or VTT selected")
        self._sync_caption_controls()
        if self.video_path:
            self.status_label.setText("Ready - no captions; scanning the full video")

    def start_scan(self) -> None:
        if self.video_path is None:
            QMessageBox.information(self, "Choose a video", "Choose or drop a video before scanning.")
            return
        if self.run_combo.currentData() and self.caption_path is None:
            QMessageBox.information(self, "Choose captions", "Super Speed Run needs an SRT or VTT caption file.")
            return
        try:
            start_seconds = self._optional_timestamp(self.start_time_input.text())
            end_seconds = self._optional_timestamp(self.end_time_input.text())
        except ValueError as exc:
            QMessageBox.information(self, "Check timestamps", str(exc))
            return
        settings = ScanSettings(
            mode=str(self.mode_combo.currentData()),
            gaps_only=bool(self.run_combo.currentData()),
            custom_frame_step=self.custom_frame_step.value(),
            min_ocr_confidence=0.0,
            review_breadth=self.breadth_slider.value() / 100.0,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            caption_path=self.caption_path,
            auto_find_captions=self.auto_find_captions,
            only_dialogue_gaps=self.gap_only_check.isChecked(),
            minimum_dialogue_gap_seconds=self.minimum_gap_slider.value() / 10.0,
            enable_scene_detection=self.scene_detection_check.isChecked(),
            reuse_unchanged_frames=self.reuse_check.isChecked(),
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
        self.status_label.setText("Finding dialogue gaps..." if settings.gaps_only else "Preparing scan...")
        self.thread.start()

    def cancel_scan(self) -> None:
        if self.thread:
            self.thread.cancel()
            self.status_label.setText("Cancelling...")
            self.cancel_button.setEnabled(False)

    def update_progress(self, progress: ScanProgress) -> None:
        self.progress.setValue(int(progress.fraction * 1000))
        if progress.frames_processed:
            detail = (
                f"{format_timestamp(progress.current_seconds)} / "
                f"{format_timestamp(progress.scan_end_seconds)} - "
                f"{progress.detections_found} detections"
            )
        else:
            detail = progress.filename
        self.status_label.setText(f"{progress.phase} - {detail}")

    def scan_finished(self, result: object) -> None:
        self.output_dir = result.output_dir
        self.report_path = result.report_html
        self.progress.setValue(1000)
        if isinstance(result, DialogueGapResult):
            self.status_label.setText(
                f"Complete in {format_timestamp(result.elapsed_seconds)} - "
                f"{len(result.gaps)} dialogue gaps; no OCR run"
            )
        else:
            counts = bucket_counts(result.events)
            self.status_label.setText(
                f"Complete in {format_timestamp(result.elapsed_seconds)} - "
                f"{counts[LIKELY_FORCED_TEXT]} likely forced text, "
                f"{counts[NEEDS_REVIEW]} to review"
            )
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

    def open_report(self) -> None:
        if self.report_path:
            subprocess.run(["open", str(self.report_path)], check=False)

    def _toggle_advanced(self, checked: bool) -> None:
        self.advanced_group.setVisible(checked)
        self.advanced_toggle.setText("Hide Advanced Settings" if checked else "Show Advanced Settings")
        if checked:
            QTimer.singleShot(0, lambda: self.scroll_area.ensureWidgetVisible(self.advanced_group))

    def _sync_scan_mode_controls(self, _index: int = -1) -> None:
        self.custom_frame_step.setEnabled(self.mode_combo.currentData() == "custom")
        self.reuse_check.setEnabled(self.mode_combo.currentData() != "advanced")

    def _sync_caption_controls(self, _checked: bool = False) -> None:
        self.run_combo.model().item(1).setEnabled(self.caption_path is not None)
        if self.caption_path is None and self.run_combo.currentData():
            self.run_combo.setCurrentIndex(0)
        self.minimum_gap_slider.setEnabled(
            self.caption_path is not None
            and (bool(self.run_combo.currentData()) or self.gap_only_check.isChecked())
        )

    def _sync_run_controls(self, _index: int = -1) -> None:
        gaps_only = bool(self.run_combo.currentData())
        self.scan_button.setText("Find Dialogue Gaps" if gaps_only else "Scan Video")
        self.gap_only_check.setEnabled(not gaps_only)
        self.advanced_group.setEnabled(not gaps_only)
        self._sync_caption_controls()

    def _update_minimum_gap_label(self, value: int) -> None:
        self.minimum_gap_value.setText(f"{value / 10:.1f} s")

    def _update_breadth_label(self, value: int) -> None:
        if value <= 25:
            label = "Broad review"
        elif value >= 75:
            label = "Focused review"
        else:
            label = "Balanced"
        self.breadth_value.setText(label)

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
