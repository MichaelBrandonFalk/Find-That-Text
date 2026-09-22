from __future__ import annotations

from find_that_text.tracking.events import OCRDetection, TextEvent
from find_that_text.tracking.moments import group_screen_text_moments


def detection(text: str, y: float) -> OCRDetection:
    return OCRDetection(
        timestamp_seconds=4.0,
        text=text,
        confidence=0.9,
        polygon=[[600, y], [1320, y], [1320, y + 60], [600, y + 60]],
        box=(600, y, 720, 60),
        frame_width=1920,
        frame_height=1080,
        frame_index=96,
        source_filename="feature.mov",
    )


def test_nearby_lines_become_one_screen_text_moment() -> None:
    moments = group_screen_text_moments(
        [
            TextEvent(event_id=1, detections=[detection("PARIS", 420)]),
            TextEvent(event_id=2, detections=[detection("THREE YEARS LATER", 500)]),
        ],
        sample_interval_seconds=1.0,
    )

    assert len(moments) == 1
    assert moments[0].text == "PARIS / THREE YEARS LATER"


def test_sequential_cards_in_same_location_remain_separate() -> None:
    first = detection("ONE YEAR LATER", 450)
    second = detection("PARIS", 450)
    second.timestamp_seconds = 5.0
    second.frame_index = 120

    moments = group_screen_text_moments(
        [
            TextEvent(event_id=1, detections=[first]),
            TextEvent(event_id=2, detections=[second]),
        ],
        sample_interval_seconds=2.0,
    )

    assert len(moments) == 2
