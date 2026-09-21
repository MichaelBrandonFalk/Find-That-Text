from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from find_that_text.reports.csv_report import write_csv_report
from find_that_text.reports.html_report import write_html_report
from find_that_text.reports.raw_json import write_raw_json
from find_that_text.tracking.events import OCRDetection, TextEvent
from find_that_text.video.metadata import VideoMetadata
from find_that_text.video.sampling import ScanMode


def test_reports_write_expected_files(tmp_path: Path) -> None:
    detection = OCRDetection(
        timestamp_seconds=3.5,
        text="HELLO WORLD",
        confidence=0.9,
        polygon=[[100, 100], [300, 100], [300, 150], [100, 150]],
        box=(100, 100, 200, 50),
        frame_width=1920,
        frame_height=1080,
        frame_index=7,
        source_filename="fixture.mov",
    )
    event = TextEvent(event_id=1, detections=[detection], screenshot="screenshots/0001.jpg")
    metadata = VideoMetadata(
        path=tmp_path / "fixture.mov",
        filename="fixture.mov",
        duration_seconds=30.0,
        width=1920,
        height=1080,
        average_rate=Fraction(24, 1),
        codec_name="h264",
        frame_count=720,
    )
    scan_mode = ScanMode("standard", 0.5)

    write_csv_report(tmp_path / "report.csv", [event])
    write_html_report(
        tmp_path / "report.html",
        events=[event],
        metadata=metadata,
        scan_mode=scan_mode,
        ocr_model="test-model",
        min_ocr_confidence=0.75,
    )
    write_raw_json(
        tmp_path / "raw_detections.json",
        detections=[detection],
        events=[event],
        metadata=metadata,
        scan_mode=scan_mode,
        ocr_model="test-model",
        min_ocr_confidence=0.75,
    )

    assert "HELLO WORLD" in (tmp_path / "report.csv").read_text(encoding="utf-8")
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    raw_json = (tmp_path / "raw_detections.json").read_text(encoding="utf-8")
    assert "HELLO WORLD" in html
    assert "Minimum confidence 75%" in html
    assert '"detections"' in raw_json
    assert '"minimum_ocr_confidence": 0.75' in raw_json
