from __future__ import annotations

from find_that_text.tracking.events import OCRDetection
from find_that_text.tracking.matcher import track_detections


def detection(timestamp: float, text: str, x: float, y: float) -> OCRDetection:
    return OCRDetection(
        timestamp_seconds=timestamp,
        text=text,
        confidence=0.95,
        polygon=[[x, y], [x + 200, y], [x + 200, y + 40], [x, y + 40]],
        box=(x, y, 200, 40),
        frame_width=1920,
        frame_height=1080,
        frame_index=int(timestamp * 2),
        source_filename="fixture.mov",
    )


def test_ocr_fluctuations_track_as_one_event() -> None:
    detections = [
        detection(0.0, "JOHN SMITH", 100, 800),
        detection(0.5, "JOHN SMlTH", 102, 801),
        detection(1.0, "JOHN SM1TH", 101, 799),
        detection(1.5, "JOHN SMITH", 103, 800),
    ]
    events = track_detections(detections, sample_interval_seconds=0.5)
    assert len(events) == 1
    assert events[0].text == "JOHN SMITH"
    assert len(events[0].detections) == 4


def test_identical_words_in_different_locations_stay_separate() -> None:
    detections = [
        detection(0.0, "SALE", 100, 100),
        detection(0.0, "SALE", 1500, 900),
    ]
    events = track_detections(detections, sample_interval_seconds=0.5)
    assert len(events) == 2


def test_persistent_text_is_one_event() -> None:
    detections = [detection(i * 5.0, "PURE FLIX", 1650, 70) for i in range(20)]
    events = track_detections(detections, sample_interval_seconds=5.0)
    assert len(events) == 1
    assert events[0].persistent
    assert events[0].classification == "Likely persistent graphic"
