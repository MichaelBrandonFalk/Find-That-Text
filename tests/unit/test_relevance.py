from __future__ import annotations

from pathlib import Path

from find_that_text.captions import CaptionTimeline
from find_that_text.tracking.events import OCRDetection, TextEvent
from find_that_text.tracking.relevance import BACKGROUND, LIKELY_FORCED_TEXT, NEEDS_REVIEW, score_text_events


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


def test_dense_readable_signage_and_job_screen_are_not_credits() -> None:
    bakery = TextEvent(
        event_id=112,
        detections=[
            detection(t, "BAKERY / SPECIAL TODAY / CHRISTMAS / PECAN PIE", box=(497, 25, 780, 130))
            for t in (265.5, 267.0, 268.6)
        ],
    )
    job_screen = TextEvent(
        event_id=215,
        detections=[
            detection(t, "File Eat View / WORKSource.com / Post a Job / General Information / ‚ë†", box=(257, 82, 576, 442))
            for t in (417.5, 418.3, 419.0)
        ],
    )
    long_hold = TextEvent(
        event_id=272,
        detections=[
            detection(t, "WORKSource.com / Job Center / You Have 8 New Applicants! / Job Posts", box=(235, 21, 722, 409))
            for t in (531.8, 533.0, 534.1)
        ],
    )
    nearby = [
        TextEvent(event_id=1000 + index, detections=[detection(266 + index * 0.3, "X", box=(20, 20, 30, 20))])
        for index in range(12)
    ]

    score_text_events([bakery, job_screen, long_hold, *nearby])

    for event in (bakery, job_screen, long_hold):
        assert event.review_bucket == LIKELY_FORCED_TEXT
        assert not event.credit_sequence
        assert any("recognizable words" in reason for reason in event.relevance_reasons)
    assert "held on screen" in long_hold.relevance_reasons


def test_readable_words_outrank_noisy_ocr_even_with_high_confidence() -> None:
    readable = TextEvent(
        event_id=127,
        detections=[
            detection(t, "Berry / Cherry / Almond / TOQNDGAN", box=(361, 241, 674, 58))
            for t in (280.0, 281.0)
        ],
    )
    noise = TextEvent(
        event_id=307,
        detections=[
            detection(t, "9√óÔºâ / OXX", box=(550, 168, 112, 269), confidence=1.0)
            for t in (600.0, 601.0, 602.0)
        ],
    )

    score_text_events([noise, readable])

    assert readable.review_bucket == LIKELY_FORCED_TEXT
    assert noise.review_bucket in {NEEDS_REVIEW, BACKGROUND}
    assert readable.relevance_score > noise.relevance_score
    assert "no common English/Spanish words recognized" in noise.relevance_reasons


def test_spanish_sign_is_readable_and_unknown_title_is_still_reviewable() -> None:
    sign = TextEvent(
        event_id=1,
        detections=[
            detection(t, "ATENCIÓN / SALIDA / PELIGRO", box=(500, 350, 920, 120))
            for t in (2.0, 3.0)
        ],
    )
    proper_name = TextEvent(
        event_id=2,
        detections=[
            detection(t, "LINEHAM", box=(500, 350, 920, 120))
            for t in (5.0, 6.0, 7.0)
        ],
    )

    repeated_names = [
        TextEvent(event_id=event_id, detections=[
            detection(timestamp, "LINEHAM", box=(500, 350, 920, 120))
        ])
        for event_id, timestamp in ((3, 20.0), (4, 30.0))
    ]
    score_text_events([sign, proper_name, *repeated_names])

    assert sign.review_bucket == LIKELY_FORCED_TEXT
    assert proper_name.review_bucket == NEEDS_REVIEW
    assert not proper_name.repeated_graphic


def test_repeated_symbol_is_not_likely_even_with_broad_review() -> None:
    event = TextEvent(
        event_id=1,
        detections=[
            detection(t, "X", box=(500, 350, 920, 120), confidence=1.0)
            for t in (2.0, 3.0, 4.0)
        ],
    )

    score_text_events([event], review_breadth=0.0)

    assert event.review_bucket != LIKELY_FORCED_TEXT
