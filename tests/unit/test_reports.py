from __future__ import annotations

from fractions import Fraction
from io import BytesIO
from pathlib import Path
import base64
import re
from xml.etree import ElementTree
from zipfile import ZipFile

from PIL import Image

from find_that_text.reports.csv_report import write_csv_report
from find_that_text.reports.html_report import write_html_report
from find_that_text.reports.raw_json import write_raw_json
from find_that_text.reports.xlsx_report import REVIEW_COLUMNS, write_xlsx_report
from find_that_text.tracking.events import OCRDetection, TextEvent
from find_that_text.tracking.relevance import BACKGROUND
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
    event = TextEvent(
        event_id=1,
        detections=[detection],
        screenshot="screenshots/0001.jpg",
        annotated_screenshot="screenshots/0001_annotated.jpg",
        review_bucket=BACKGROUND,
    )
    (tmp_path / "screenshots").mkdir()
    Image.new("RGB", (1600, 900), "#234567").save(tmp_path / event.screenshot)
    Image.new("RGB", (1600, 900), "#345678").save(tmp_path / event.annotated_screenshot)
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
    write_xlsx_report(tmp_path / "report.xlsx", [event])
    write_html_report(
        tmp_path / "report.html",
        events=[event],
        metadata=metadata,
        scan_mode=scan_mode,
        ocr_model="test-model",
        min_ocr_confidence=0.75,
        ocr_frames=4,
        reused_frames=2,
        elapsed_seconds=74.2,
        minimum_dialogue_gap_seconds=1.0,
    )
    write_html_report(
        tmp_path / "shareable_report.html",
        events=[event],
        metadata=metadata,
        scan_mode=scan_mode,
        ocr_model="test-model",
        standalone=True,
    )
    write_raw_json(
        tmp_path / "raw_detections.json",
        detections=[detection],
        events=[event],
        metadata=metadata,
        scan_mode=scan_mode,
        ocr_model="test-model",
        min_ocr_confidence=0.75,
        ocr_frames=4,
        reused_frames=2,
        elapsed_seconds=74.2,
        minimum_dialogue_gap_seconds=1.0,
    )

    assert "HELLO WORLD" in (tmp_path / "report.csv").read_text(encoding="utf-8")
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    raw_json = (tmp_path / "raw_detections.json").read_text(encoding="utf-8")
    assert "HELLO WORLD" in html
    assert 'href="screenshots/0001.jpg"' in html
    assert "Open screenshot" in html
    assert 'href="report.xlsx"' in html
    assert REVIEW_COLUMNS[:6] == [
        "Detected Text",
        "Start Time",
        "End Time",
        "Relevance Score",
        "Review Bucket",
        "Evidence Screenshot",
    ]
    with ZipFile(tmp_path / "report.xlsx") as archive:
        worksheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        relationships = ElementTree.fromstring(
            archive.read("xl/worksheets/_rels/sheet1.xml.rels")
        )
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    cells = worksheet.findall(".//s:hyperlink", ns)
    assert {cell.attrib["ref"] for cell in cells} == {"F2", "G2"}
    targets = {item.attrib["Target"].replace("\\", "/") for item in relationships}
    assert targets == {"screenshots/0001.jpg", "screenshots/0001_annotated.jpg"}
    assert "Likely Forced Text" in html
    assert "Needs Review" in html
    assert "Less Likely" in html
    assert "Minimum confidence 75%" in html
    assert "4 frames analyzed, 2 reused" in html
    assert "Scan Time</strong><br>00:01:14.200" in html
    assert "Minimum Dialogue Gap</strong><br>1 s" in html
    assert '"detections"' in raw_json
    assert '"minimum_ocr_confidence": 0.75' in raw_json
    assert '"schema_version": 3' in raw_json
    assert '"review_bucket": "Less Likely"' in raw_json
    assert "Less Likely" in (tmp_path / "report.csv").read_text(encoding="utf-8")
    assert '"ocr_frames_analyzed": 4' in raw_json
    assert '"ocr_frames_reused": 2' in raw_json
    assert '"elapsed_seconds": 74.2' in raw_json
    assert '"minimum_dialogue_gap_seconds": 1.0' in raw_json

    shareable = (tmp_path / "shareable_report.html").read_text(encoding="utf-8")
    assert "Less Likely" in shareable
    assert '<dialog id="frame-viewer">' in shareable
    assert 'href="screenshots/' not in shareable
    assert 'src="screenshots/' not in shareable
    assert 'href="report.xlsx"' not in shareable
    assert 'href="dialogue_gaps.html"' not in shareable
    references = re.findall(r'(?:href|src)="([^"]+)"', shareable)
    assert references and all(reference.startswith("data:") for reference in references)
    embedded = re.search(r'src="data:image/jpeg;base64,([^"]+)"', shareable)
    assert embedded is not None
    with Image.open(BytesIO(base64.b64decode(embedded.group(1)))) as image:
        assert image.size == (1280, 720)


def test_spreadsheet_does_not_turn_ocr_text_into_a_formula(tmp_path: Path) -> None:
    detection = OCRDetection(
        timestamp_seconds=1.0,
        text='=HYPERLINK("https://example.com", "click")',
        confidence=0.9,
        polygon=[],
        box=(0, 0, 100, 30),
        frame_width=1920,
        frame_height=1080,
        frame_index=24,
        source_filename="fixture.mov",
    )
    event = TextEvent(event_id=1, detections=[detection])
    write_xlsx_report(tmp_path / "report.xlsx", [event])

    with ZipFile(tmp_path / "report.xlsx") as archive:
        worksheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        shared_strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    assert worksheet.findall(".//s:f", ns) == []
    assert worksheet.findall(".//s:hyperlink", ns) == []
    assert "HYPERLINK" in shared_strings
