from __future__ import annotations

import re
from collections import Counter
from functools import lru_cache

from wordfreq import zipf_frequency

from find_that_text.captions import CaptionTimeline
from find_that_text.ocr.normalize import normalize_text
from find_that_text.tracking.events import TextEvent


LIKELY_FORCED_TEXT = "Likely Forced Text"
NEEDS_REVIEW = "Needs Review"
BACKGROUND = "Less Likely"
_WORD = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_WEB_TOKENS = {"com", "http", "https", "net", "org", "www"}


def score_text_events(
    events: list[TextEvent],
    *,
    caption_timeline: CaptionTimeline | None = None,
    scene_change_times: list[float] | None = None,
    review_breadth: float = 0.5,
) -> list[TextEvent]:
    breadth = min(1.0, max(0.0, float(review_breadth)))
    scene_change_times = scene_change_times or []
    text_counts = Counter(normalize_text(event.text) for event in events if normalize_text(event.text))

    for event in events:
        _score_event(
            event,
            caption_timeline=caption_timeline,
            scene_change_times=scene_change_times,
            repeated_count=text_counts[normalize_text(event.text)],
            review_breadth=breadth,
        )
    return sorted(events, key=lambda event: (event.bucket_rank, -event.relevance_score, event.start_seconds))


def _score_event(
    event: TextEvent,
    *,
    caption_timeline: CaptionTimeline | None,
    scene_change_times: list[float],
    repeated_count: int,
    review_breadth: float,
) -> None:
    score = 0.12
    reasons: list[str] = []
    text = event.text.strip()
    compact = re.sub(r"\s+", "", text)
    alphanumeric_count = sum(character.isalnum() for character in compact)
    recognizable_words = _recognizable_words(text)

    score += min(0.24, event.maximum_confidence * 0.24)
    if event.maximum_detector_confidence is not None:
        score += min(0.1, event.maximum_detector_confidence * 0.1)

    timestamp_count = len({round(detection.timestamp_seconds, 3) for detection in event.detections})
    if timestamp_count >= 3:
        score += 0.22
        reasons.append("confirmed across frames")
    elif timestamp_count == 2:
        score += 0.14
        reasons.append("seen twice")
    else:
        score -= 0.04
    if timestamp_count >= 3 and event.duration_seconds >= 2:
        score += 0.05
        reasons.append("held on screen")

    single_symbol = alphanumeric_count <= 1
    if single_symbol:
        score -= 0.34
        reasons.append("isolated symbol or character")
    elif len(recognizable_words) >= 4:
        score += 0.2
        reasons.append("several recognizable words")
    elif len(recognizable_words) >= 2:
        score += 0.16
        reasons.append("recognizable words")
    elif recognizable_words:
        score += 0.06
        reasons.append("recognizable word")
    else:
        score -= 0.22
        reasons.append("no common English/Spanish words recognized")
        if sum(not character.isalnum() and not character.isspace() for character in text) > len(text) * 0.2:
            score -= 0.1
            reasons.append("symbol-heavy OCR")

    best = event.best_detection
    area_ratio = 0.0
    width_ratio = 0.0
    height_ratio = 0.0
    if best and best.frame_width > 0 and best.frame_height > 0:
        _x, _y, width, height = event.bounding_box
        area_ratio = (width * height) / (best.frame_width * best.frame_height)
        width_ratio = width / best.frame_width
        height_ratio = height / best.frame_height
    if area_ratio < 0.00025:
        score -= 0.14
        reasons.append("very small on screen")
    elif area_ratio >= 0.002:
        score += 0.07

    title_like = (
        event.position == "Center"
        and (width_ratio >= 0.22 or height_ratio >= 0.07)
        and not single_symbol
        and event.start_seconds <= 15 * 60
    )
    if title_like:
        score += 0.2
        reasons.append("large centered title")

    timestamps = sorted({detection.timestamp_seconds for detection in event.detections})
    if caption_timeline is not None:
        event.dialogue_free_ratio = caption_timeline.dialogue_free_ratio(timestamps)
        if event.dialogue_free_ratio >= 0.75:
            score += 0.16
            reasons.append("appears in a dialogue gap")
        elif event.dialogue_free_ratio <= 0.25:
            reasons.append("overlaps dialogue")

    if any(abs(event.start_seconds - cut) <= 1.0 for cut in scene_change_times):
        event.near_scene_change = True
        score += 0.05
        reasons.append("near a scene change")

    corner = event.position in {"Upper Left", "Upper Right", "Lower Left", "Lower Right"}
    repeated_graphic = corner and area_ratio < 0.012 and (
        event.duration_seconds >= 12 or repeated_count >= 3
    )
    if repeated_graphic:
        score -= 0.32
        reasons.append("persistent or repeated graphic")

    score = min(1.0, max(0.0, score))
    likely_threshold = 0.64 + (review_breadth - 0.5) * 0.24
    review_threshold = 0.36 + (review_breadth - 0.5) * 0.2

    if repeated_graphic:
        bucket = BACKGROUND
    elif not recognizable_words:
        bucket = NEEDS_REVIEW if score >= review_threshold else BACKGROUND
    elif score >= likely_threshold:
        bucket = LIKELY_FORCED_TEXT
    elif score >= review_threshold:
        bucket = NEEDS_REVIEW
    else:
        bucket = BACKGROUND

    event.relevance_score = score
    event.review_bucket = bucket
    event.relevance_reasons = reasons or ["limited supporting evidence"]
    event.title_like = title_like
    event.credit_sequence = False
    event.repeated_graphic = repeated_graphic


def bucket_counts(events: list[TextEvent]) -> dict[str, int]:
    counts = {LIKELY_FORCED_TEXT: 0, NEEDS_REVIEW: 0, BACKGROUND: 0}
    for event in events:
        counts[event.review_bucket] = counts.get(event.review_bucket, 0) + 1
    return counts


def _recognizable_words(text: str) -> set[str]:
    words = _WORD.findall(_CAMEL_BOUNDARY.sub(" ", text))
    return {
        word.casefold()
        for word in words
        if word.casefold() not in _WEB_TOKENS and _is_recognizable_word(word.casefold())
    }


@lru_cache(maxsize=20_000)
def _is_recognizable_word(word: str) -> bool:
    return max(
        zipf_frequency(word, "en", wordlist="small"),
        zipf_frequency(word, "es", wordlist="small"),
    ) >= 3.0
