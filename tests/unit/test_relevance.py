from __future__ import annotations

from pathlib import Path

from find_that_text.captions import CaptionTimeline
from find_that_text.tracking.events import OCRDetection, TextEvent
from find_that_text.tracking.relevance import BACKGROUND, LIKELY_FORCED_TEXT, score_text_events


def detection(
    timestamp: float,
    text: str,
    *,
    box: tuple[float, float, float, float],
    confidence: float = 0.9,
) -> OCRDetection:
    x, y, width, height = box
    return OCRDetection(
        timestamp_seconds=timestamp,
        text=text,
        confidence=confidence,
        polygon=[[x, y], [x + width, y], [x + width, y + height], [x, y + height]],
        box=box,
        frame_width=1920,
        frame_height=1080,
        frame_index=int(timestamp * 24),
        source_filename="feature.mov",
        detector_confidence=0.9,
    )


def caption_timeline(tmp_path: Path) -> CaptionTimeline:
    path = tmp_path / "feature.srt"
    path.write_text("1\n00:00:10,000 --> 00:00:20,000\nDialogue\n", encoding="utf-8")
    return CaptionTimeline.from_file(path)


def test_large_centered_title_in_dialogue_gap_is_likely(tmp_path: Path) -> None:
    event = TextEvent(
        event_id=1,
        detections=[
            detection(2.0, "THE LAST TRAIN", box=(500, 350, 920, 120), confidence=0.45),
            detection(3.0, "THE LAST TRAIN", box=(500, 350, 920, 120), confidence=0.5),
        ],
    )

    score_text_events([event], caption_timeline=caption_timeline(tmp_path))

    assert event.review_bucket == LIKELY_FORCED_TEXT
    assert event.title_like
    assert "appears in a dialogue gap" in event.relevance_reasons


def test_lone_decorative_x_is_preserved_but_not_promoted(tmp_path: Path) -> None:
    event = TextEvent(
        event_id=1,
        detections=[detection(2.0, "X", box=(850, 450, 220, 180), confidence=0.99)],
    )

    score_text_events([event], caption_timeline=caption_timeline(tmp_path))

    assert event.review_bucket == BACKGROUND
    assert "isolated symbol or character" in event.relevance_reasons


def test_persistent_corner_text_is_collapsed() -> None:
    event = TextEvent(
        event_id=1,
        detections=[
            detection(float(second), "NETWORK", box=(1650, 40, 200, 45))
            for second in range(0, 20, 2)
        ],
    )

    score_text_events([event])

    assert event.review_bucket == BACKGROUND
    assert event.repeated_graphic
