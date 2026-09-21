from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from find_that_text.tracking.events import OCRDetection, TextEvent
from find_that_text.util.timestamps import format_timestamp


def save_event_screenshots(
    video_path: str | Path,
    events: list[TextEvent],
    screenshots_dir: Path,
    *,
    annotated: bool = False,
) -> None:
    targets = [
        (event.best_detection.timestamp_seconds, event)
        for event in events
        if event.best_detection is not None
    ]
    if not targets:
        return

    try:
        import av
    except ImportError as exc:  # pragma: no cover - exercised in dependency spike
        raise RuntimeError("PyAV is required to save evidence screenshots.") from exc

    targets.sort(key=lambda item: item[0])
    target_index = 0
    last_image: Image.Image | None = None
    last_timestamp = 0.0

    with av.open(str(video_path)) as container:
        stream = container.streams.video[0]
        for frame in container.decode(stream):
            timestamp = frame.time
            if timestamp is None:
                if frame.pts is None or frame.time_base is None:
                    continue
                timestamp = float(frame.pts * frame.time_base)
            image = Image.fromarray(frame.to_ndarray(format="rgb24"))
            last_image = image
            last_timestamp = float(timestamp)

            while target_index < len(targets) and timestamp + 1e-6 >= targets[target_index][0]:
                _save_event_image(targets[target_index][1], image, screenshots_dir, annotated=annotated)
                target_index += 1
            if target_index >= len(targets):
                break

    while target_index < len(targets) and last_image is not None:
        _save_event_image(targets[target_index][1], last_image, screenshots_dir, annotated=annotated)
        target_index += 1
    del last_timestamp


def _save_event_image(
    event: TextEvent,
    image: Image.Image,
    screenshots_dir: Path,
    *,
    annotated: bool,
) -> None:
    best = event.best_detection
    if best is None:
        return
    timestamp_name = format_timestamp(best.timestamp_seconds).replace(":", "-").replace(".", "-")
    base_name = f"{event.event_id:04d}_{timestamp_name}.jpg"
    clean_path = screenshots_dir / base_name
    image.save(clean_path, quality=92)
    event.screenshot = f"screenshots/{base_name}"

    if annotated:
        annotated_image = image.copy()
        _draw_annotation(annotated_image, best)
        annotated_name = f"{event.event_id:04d}_{timestamp_name}_annotated.jpg"
        annotated_path = screenshots_dir / annotated_name
        annotated_image.save(annotated_path, quality=92)
        event.annotated_screenshot = f"screenshots/{annotated_name}"


def _draw_annotation(image: Image.Image, detection: OCRDetection) -> None:
    draw = ImageDraw.Draw(image)
    polygon = [tuple(point) for point in detection.polygon]
    if polygon:
        draw.line([*polygon, polygon[0]], fill=(0, 220, 180), width=4)
    x, y, width, _height = detection.box
    label = f"{detection.text} {detection.confidence:.2f}"
    draw.rectangle((x, max(0, y - 24), x + max(width, 160), y), fill=(0, 0, 0))
    draw.text((x + 4, max(0, y - 20)), label, fill=(255, 255, 255))
