from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - fallback only used without optional dependency
    fuzz = None

from find_that_text.ocr.normalize import normalize_text
from find_that_text.tracking.events import OCRDetection, TextEvent
from find_that_text.tracking.geometry import box_iou, center_distance_ratio


@dataclass(slots=True)
class TrackingConfig:
    text_similarity_threshold: float = 86.0
    max_center_distance_ratio: float = 0.12
    min_iou: float = 0.08
    max_gap_seconds: float = 1.5


def text_similarity(a: str, b: str) -> float:
    left = normalize_text(a)
    right = normalize_text(b)
    if not left or not right:
        return 0.0
    if left == right:
        return 100.0
    if fuzz is not None:
        return float(fuzz.ratio(left, right))
    return SequenceMatcher(None, left, right).ratio() * 100


def _event_matches(event: TextEvent, detection: OCRDetection, config: TrackingConfig) -> bool:
    last = max(event.detections, key=lambda d: d.timestamp_seconds)
    if detection.timestamp_seconds - last.timestamp_seconds > config.max_gap_seconds:
        return False
    if text_similarity(event.text, detection.text) < config.text_similarity_threshold:
        return False
    iou = box_iou(event.bounding_box, detection.box)
    center_distance = center_distance_ratio(
        event.bounding_box,
        detection.box,
        detection.frame_width,
        detection.frame_height,
    )
    return iou >= config.min_iou or center_distance <= config.max_center_distance_ratio


def track_detections(
    detections: list[OCRDetection],
    *,
    sample_interval_seconds: float = 0.5,
    config: TrackingConfig | None = None,
) -> list[TextEvent]:
    if config is None:
        config = TrackingConfig(max_gap_seconds=max(1.25, sample_interval_seconds * 2.5))

    events: list[TextEvent] = []
    active: list[TextEvent] = []

    for detection in sorted(detections, key=lambda d: (d.timestamp_seconds, d.text)):
        active = [
            event
            for event in active
            if detection.timestamp_seconds - event.end_seconds <= config.max_gap_seconds
        ]
        candidates = [event for event in active if _event_matches(event, detection, config)]
        if candidates:
            best = max(
                candidates,
                key=lambda event: (
                    text_similarity(event.text, detection.text),
                    box_iou(event.bounding_box, detection.box),
                ),
            )
            best.detections.append(detection)
            continue

        event = TextEvent(event_id=len(events) + 1, detections=[detection])
        events.append(event)
        active.append(event)

    for index, event in enumerate(sorted(events, key=lambda e: e.start_seconds), start=1):
        event.event_id = index
    return events
