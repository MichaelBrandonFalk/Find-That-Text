from __future__ import annotations

from find_that_text.tracking.events import TextEvent
from find_that_text.tracking.geometry import center_distance_ratio


def group_screen_text_moments(
    events: list[TextEvent],
    *,
    sample_interval_seconds: float,
) -> list[TextEvent]:
    grouped: list[TextEvent] = []
    time_tolerance = max(0.08, min(0.25, sample_interval_seconds * 0.15))

    for event in sorted(events, key=lambda item: (item.start_seconds, item.position)):
        match = next(
            (
                candidate
                for candidate in reversed(grouped[-20:])
                if _events_share_moment(candidate, event, time_tolerance=time_tolerance)
            ),
            None,
        )
        if match is None:
            grouped.append(TextEvent(event_id=len(grouped) + 1, detections=list(event.detections)))
        else:
            match.detections.extend(event.detections)

    grouped.sort(key=lambda item: item.start_seconds)
    for index, event in enumerate(grouped, start=1):
        event.event_id = index
    return grouped


def _events_share_moment(left: TextEvent, right: TextEvent, *, time_tolerance: float) -> bool:
    left_timestamps = {detection.timestamp_seconds for detection in left.detections}
    right_timestamps = {detection.timestamp_seconds for detection in right.detections}
    if not any(
        abs(left_timestamp - right_timestamp) <= time_tolerance
        for left_timestamp in left_timestamps
        for right_timestamp in right_timestamps
    ):
        return False
    left_best = left.best_detection
    right_best = right.best_detection
    if left_best is None or right_best is None:
        return False
    spatial_distance = center_distance_ratio(
        left.bounding_box,
        right.bounding_box,
        left_best.frame_width,
        left_best.frame_height,
    )
    return spatial_distance <= 0.34
