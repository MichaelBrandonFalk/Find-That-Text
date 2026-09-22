from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from find_that_text.tracking.geometry import classify_position, union_box
from find_that_text.ocr.normalize import normalize_text
from find_that_text.util.timestamps import format_timestamp


@dataclass(slots=True)
class OCRDetection:
    timestamp_seconds: float
    text: str
    confidence: float
    polygon: list[list[float]]
    box: tuple[float, float, float, float]
    frame_width: int
    frame_height: int
    frame_index: int
    source_filename: str
    detector_confidence: float | None = None

    @property
    def timestamp(self) -> str:
        return format_timestamp(self.timestamp_seconds)

    def to_json(self) -> dict[str, Any]:
        return {
            "timestamp_seconds": round(self.timestamp_seconds, 3),
            "timestamp": self.timestamp,
            "text": self.text,
            "confidence": round(float(self.confidence), 6),
            "detector_confidence": (
                round(float(self.detector_confidence), 6)
                if self.detector_confidence is not None
                else None
            ),
            "polygon": self.polygon,
            "box": {
                "x": round(self.box[0], 3),
                "y": round(self.box[1], 3),
                "width": round(self.box[2], 3),
                "height": round(self.box[3], 3),
            },
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "frame_index": self.frame_index,
            "source_filename": self.source_filename,
            "position": classify_position(self.box, self.frame_width, self.frame_height),
        }


@dataclass(slots=True)
class TextEvent:
    event_id: int
    detections: list[OCRDetection] = field(default_factory=list)
    screenshot: str = ""
    annotated_screenshot: str = ""
    relevance_score: float = 0.0
    review_bucket: str = "Needs Review"
    relevance_reasons: list[str] = field(default_factory=list)
    dialogue_free_ratio: float | None = None
    near_scene_change: bool = False
    title_like: bool = False
    credit_sequence: bool = False
    repeated_graphic: bool = False

    @property
    def start_seconds(self) -> float:
        return min((d.timestamp_seconds for d in self.detections), default=0.0)

    @property
    def end_seconds(self) -> float:
        return max((d.timestamp_seconds for d in self.detections), default=0.0)

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.end_seconds - self.start_seconds)

    @property
    def text(self) -> str:
        if not self.detections:
            return ""
        timestamp_groups: dict[float, list[OCRDetection]] = {}
        for detection in self.detections:
            timestamp_groups.setdefault(round(detection.timestamp_seconds, 3), []).append(detection)
        representative = max(
            timestamp_groups.values(),
            key=lambda group: sum(len(detection.text.strip()) * detection.confidence for detection in group),
        )
        lines: list[str] = []
        seen: set[str] = set()
        for detection in sorted(representative, key=lambda item: (item.box[1], item.box[0])):
            normalized = normalize_text(detection.text)
            if normalized and normalized not in seen:
                seen.add(normalized)
                lines.append(detection.text.strip())
        return " / ".join(lines)

    @property
    def average_confidence(self) -> float:
        return mean([d.confidence for d in self.detections]) if self.detections else 0.0

    @property
    def maximum_confidence(self) -> float:
        return max((d.confidence for d in self.detections), default=0.0)

    @property
    def maximum_detector_confidence(self) -> float | None:
        values = [
            detection.detector_confidence
            for detection in self.detections
            if detection.detector_confidence is not None
        ]
        return max(values) if values else None

    @property
    def best_detection(self) -> OCRDetection | None:
        if not self.detections:
            return None
        return max(self.detections, key=lambda d: (d.confidence, len(d.text)))

    @property
    def bounding_box(self) -> tuple[float, float, float, float]:
        return union_box([d.box for d in self.detections])

    @property
    def position(self) -> str:
        best = self.best_detection
        if not best:
            return "Unknown"
        return classify_position(self.bounding_box, best.frame_width, best.frame_height)

    @property
    def classification(self) -> str:
        if self.duration_seconds >= 60:
            return "Likely persistent graphic"
        if self.duration_seconds >= 15:
            return "Persistent"
        if self.duration_seconds <= 1.0:
            return "Brief"
        return "Normal"

    @property
    def persistent(self) -> bool:
        return self.duration_seconds >= 15

    @property
    def bucket_rank(self) -> int:
        return {
            "Likely Forced Text": 0,
            "Needs Review": 1,
            "Background / Credits / Repeated Graphics": 2,
        }.get(self.review_bucket, 1)

    def to_row(self) -> dict[str, str]:
        box = self.bounding_box
        source_filename = self.detections[0].source_filename if self.detections else ""
        return {
            "Event ID": str(self.event_id),
            "Start Time": format_timestamp(self.start_seconds),
            "End Time": format_timestamp(self.end_seconds),
            "Duration": format_timestamp(self.duration_seconds),
            "Detected Text": self.text,
            "Average Confidence": f"{self.average_confidence:.3f}",
            "Maximum Confidence": f"{self.maximum_confidence:.3f}",
            "Detector Confidence": (
                f"{self.maximum_detector_confidence:.3f}"
                if self.maximum_detector_confidence is not None
                else ""
            ),
            "Relevance Score": f"{self.relevance_score:.3f}",
            "Review Bucket": self.review_bucket,
            "Why Flagged": "; ".join(self.relevance_reasons),
            "Dialogue-Free Ratio": (
                f"{self.dialogue_free_ratio:.3f}" if self.dialogue_free_ratio is not None else ""
            ),
            "Position": self.position,
            "Bounding Box": f"{box[0]:.1f},{box[1]:.1f},{box[2]:.1f},{box[3]:.1f}",
            "Detection Count": str(len(self.detections)),
            "Persistent": "yes" if self.persistent else "no",
            "Classification": self.classification,
            "Evidence Screenshot": self.screenshot,
            "Annotated Screenshot": self.annotated_screenshot,
            "Source Filename": source_filename,
        }
