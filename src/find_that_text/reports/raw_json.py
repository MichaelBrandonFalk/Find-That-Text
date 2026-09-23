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
    review_breadth: float = 0.5,
    caption_path: Path | None = None,
    dialogue_optimization: bool = False,
    dialogue_gaps_only: bool = False,
    scene_detection: bool = False,
    scene_change_times: list[float] | None = None,
    ocr_frames: int = 0,
    reused_frames: int = 0,
    minimum_dialogue_gap_seconds: float | None = None,
    elapsed_seconds: float = 0.0,
) -> None:
    detection_indexes = {id(detection): index for index, detection in enumerate(detections)}
    payload = {
        "schema_version": 2,
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
            "review_breadth": round(review_breadth, 3),
            "ocr_model": ocr_model,
            "caption_filename": caption_path.name if caption_path else None,
            "dialogue_optimization": dialogue_optimization,
            "dialogue_gaps_only": dialogue_gaps_only,
            "minimum_dialogue_gap_seconds": minimum_dialogue_gap_seconds,
            "elapsed_seconds": round(elapsed_seconds, 3),
            "scene_detection": scene_detection,
            "scene_change_times": [round(value, 3) for value in (scene_change_times or [])],
            "ocr_frames_analyzed": ocr_frames,
            "ocr_frames_reused": reused_frames,
        },
        "events": [
            {
                "event_id": event.event_id,
                "start_seconds": round(event.start_seconds, 3),
                "end_seconds": round(event.end_seconds, 3),
                "text": event.text,
                "classification": event.classification,
                "relevance_score": round(event.relevance_score, 3),
                "review_bucket": event.review_bucket,
                "relevance_reasons": event.relevance_reasons,
                "dialogue_free_ratio": (
                    round(event.dialogue_free_ratio, 3)
                    if event.dialogue_free_ratio is not None
                    else None
                ),
                "near_scene_change": event.near_scene_change,
                "title_like": event.title_like,
                "credit_sequence": event.credit_sequence,
                "repeated_graphic": event.repeated_graphic,
                "detection_indexes": [detection_indexes[id(detection)] for detection in event.detections],
            }
            for event in events
        ],
        "detections": [detection.to_json() for detection in detections],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
