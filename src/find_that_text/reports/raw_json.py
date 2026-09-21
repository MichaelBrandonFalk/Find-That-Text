from __future__ import annotations

import json
from pathlib import Path

from find_that_text.tracking.events import OCRDetection, TextEvent
from find_that_text.version import __version__
from find_that_text.video.metadata import VideoMetadata
from find_that_text.video.sampling import ScanMode


def write_raw_json(
    path: Path,
    *,
    detections: list[OCRDetection],
    events: list[TextEvent],
    metadata: VideoMetadata,
    scan_mode: ScanMode,
    ocr_model: str,
    scan_start_seconds: float = 0.0,
    scan_end_seconds: float | None = None,
    min_ocr_confidence: float = 0.0,
) -> None:
    payload = {
        "schema_version": 1,
        "application": "Find That Text",
        "application_version": __version__,
        "source": {
            "filename": metadata.filename,
            "duration_seconds": metadata.duration_seconds,
            "width": metadata.width,
            "height": metadata.height,
            "codec_name": metadata.codec_name,
            "average_rate": str(metadata.average_rate) if metadata.average_rate else None,
        },
        "scan": {
            "mode": scan_mode.name,
            "interval_seconds": scan_mode.interval_seconds,
            "frame_step": scan_mode.frame_step,
            "start_seconds": round(scan_start_seconds, 3),
            "end_seconds": round(scan_end_seconds, 3) if scan_end_seconds is not None else None,
            "minimum_ocr_confidence": round(min_ocr_confidence, 3),
            "ocr_model": ocr_model,
        },
        "events": [
            {
                "event_id": event.event_id,
                "start_seconds": round(event.start_seconds, 3),
                "end_seconds": round(event.end_seconds, 3),
                "text": event.text,
                "classification": event.classification,
                "detection_indexes": [detections.index(detection) for detection in event.detections],
            }
            for event in events
        ],
        "detections": [detection.to_json() for detection in detections],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
