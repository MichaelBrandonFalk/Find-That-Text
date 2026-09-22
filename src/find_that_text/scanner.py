from __future__ import annotations

import logging
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from find_that_text.captions import CaptionTimeline, find_sidecar_caption
from find_that_text.ocr.engine import OCREngine, OCRTextObservation, PaddleOCREngine
from find_that_text.ocr.tiling import recognize_with_optional_tiling
from find_that_text.reports.csv_report import write_csv_report
from find_that_text.reports.html_report import write_html_report
from find_that_text.reports.raw_json import write_raw_json
from find_that_text.reports.screenshots import (
    cache_candidate_frame,
    remove_candidate_cache,
    save_cached_event_screenshots,
)
from find_that_text.tracking.events import OCRDetection, TextEvent
from find_that_text.tracking.matcher import TrackingConfig, track_detections
from find_that_text.tracking.moments import group_screen_text_moments
from find_that_text.tracking.relevance import score_text_events
from find_that_text.util.logging import configure_logging
from find_that_text.util.paths import create_output_dir
from find_that_text.video.decoder import iter_sampled_frames
from find_that_text.video.metadata import VideoMetadata, read_video_metadata
from find_that_text.video.sampling import ScanMode, estimated_sample_interval_seconds, resolve_scan_mode
from find_that_text.video.scenes import detect_scene_changes

LOGGER = logging.getLogger(__name__)


class ScanCancelled(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ScanSettings:
    mode: str = "default"
    custom_frame_step: int | None = None
    custom_interval_seconds: float | None = None
    min_ocr_confidence: float = 0.0
    review_breadth: float = 0.5
    start_seconds: float | None = None
    end_seconds: float | None = None
    caption_path: str | Path | None = None
    use_dialogue_optimization: bool = True
    enable_scene_detection: bool = True
    quiet_interval_seconds: float = 0.5
    dialogue_interval_seconds: float = 2.0
    max_ocr_dimension: int = 1280
    output_root: str | Path | None = None
    save_annotated_screenshots: bool = False
    ocr_backend: str | None = None
    lang: str | None = None
    enable_uhd_tiling: str = "auto"


@dataclass(frozen=True, slots=True)
class ScanProgress:
    filename: str
    duration_seconds: float
    current_seconds: float
    frames_processed: int
    detections_found: int
    range_start_seconds: float = 0.0
    range_end_seconds: float | None = None
    phase: str = "Scanning text"

    @property
    def fraction(self) -> float:
        end_seconds = self.range_end_seconds or self.duration_seconds
        span = end_seconds - self.range_start_seconds
        if span <= 0:
            return 0.0
        current = self.current_seconds - self.range_start_seconds
        return min(1.0, max(0.0, current / span))

    @property
    def scan_end_seconds(self) -> float:
        return self.range_end_seconds or self.duration_seconds


@dataclass(frozen=True, slots=True)
class ScanResult:
    output_dir: Path
    metadata: VideoMetadata
    scan_mode: ScanMode
    detections: list[OCRDetection]
    events: list[TextEvent]
    report_html: Path
    report_csv: Path
    raw_json: Path
    caption_path: Path | None = None


ProgressCallback = Callable[[ScanProgress], None]


def scan_video(
    video_path: str | Path,
    *,
    settings: ScanSettings | None = None,
    engine: OCREngine | None = None,
    progress_callback: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
) -> ScanResult:
    settings = settings or ScanSettings()
    min_ocr_confidence = validate_min_ocr_confidence(settings.min_ocr_confidence)
    review_breadth = validate_review_breadth(settings.review_breadth)
    scan_mode = resolve_scan_mode(
        settings.mode,
        custom_frame_step=settings.custom_frame_step,
        custom_interval_seconds=settings.custom_interval_seconds,
    )
    metadata = read_video_metadata(video_path)
    start_seconds, end_seconds = _resolve_scan_range(metadata, settings)
    sample_interval_seconds = estimated_sample_interval_seconds(scan_mode, metadata.average_rate)
    output_dir = create_output_dir(video_path, settings.output_root)
    configure_logging(output_dir)
    caption_timeline = _load_caption_timeline(video_path, settings)
    scene_detection_active = settings.enable_scene_detection and scan_mode.frame_step != 1

    if progress_callback:
        progress_callback(
            ScanProgress(
                filename=metadata.filename,
                duration_seconds=metadata.duration_seconds,
                current_seconds=start_seconds,
                frames_processed=0,
                detections_found=0,
                range_start_seconds=start_seconds,
                range_end_seconds=end_seconds,
                phase="Finding scene changes" if scene_detection_active else "Preparing scan",
            )
        )

    scene_change_times: list[float] = []
    if scene_detection_active:
        scene_change_times = detect_scene_changes(
            video_path,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
        )

    LOGGER.info(
        "Starting scan filename=%s duration=%.3f resolution=%sx%s mode=%s sampling=%s range=%.3f..%s",
        metadata.filename,
        metadata.duration_seconds,
        metadata.width,
        metadata.height,
        scan_mode.name,
        scan_mode.description,
        start_seconds,
        f"{end_seconds:.3f}" if end_seconds is not None else "end",
    )
    if caption_timeline is not None:
        LOGGER.info(
            "Using dialogue timeline captions=%s cues=%d optimization=%s",
            caption_timeline.path,
            len(caption_timeline.cues),
            settings.use_dialogue_optimization,
        )

    ocr_engine = engine or PaddleOCREngine(engine=settings.ocr_backend, lang=settings.lang)
    ocr_model = getattr(ocr_engine, "model_description", getattr(ocr_engine, "name", "OCR"))
    detections: list[OCRDetection] = []
    source_filename = Path(video_path).name
    tiling_enabled = _should_tile(settings, metadata, scan_mode)
    processed_samples = 0
    cached_frames: dict[int, Path] = {}
    candidate_cache_dir = output_dir / ".candidate_frames"
    priority_timestamps = list(scene_change_times)
    interval_selector = None
    if caption_timeline is not None and settings.use_dialogue_optimization:
        priority_timestamps.extend(
            caption_timeline.quiet_gap_starts(
                start_seconds=start_seconds,
                end_seconds=end_seconds,
            )
        )
        if scan_mode.name == "default":
            interval_selector = lambda timestamp: (
                settings.dialogue_interval_seconds
                if caption_timeline.is_dialogue_active(timestamp)
                else settings.quiet_interval_seconds
            )

    for sample in iter_sampled_frames(
        video_path,
        interval_seconds=scan_mode.interval_seconds,
        frame_step=scan_mode.frame_step,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        priority_timestamps=priority_timestamps,
        interval_selector=interval_selector,
        max_dimension=None if tiling_enabled else settings.max_ocr_dimension,
    ):
        if cancel_event and cancel_event.is_set():
            LOGGER.info("Scan cancelled by user.")
            remove_candidate_cache(candidate_cache_dir)
            raise ScanCancelled("Scan cancelled.")

        processed_samples += 1
        observations = recognize_with_optional_tiling(
            ocr_engine,
            sample.image_rgb,
            enable_tiling=tiling_enabled,
        )
        kept_observations = filter_ocr_observations(observations, min_ocr_confidence)
        if kept_observations:
            cached_frames[sample.index] = cache_candidate_frame(
                sample.image_rgb,
                candidate_cache_dir,
                sample.index,
            )
        for observation in kept_observations:
            detections.append(
                OCRDetection(
                    timestamp_seconds=sample.timestamp_seconds,
                    text=observation.text,
                    confidence=observation.confidence,
                    polygon=observation.polygon,
                    box=observation.box,
                    frame_width=sample.width,
                    frame_height=sample.height,
                    frame_index=sample.index,
                    source_filename=source_filename,
                    detector_confidence=observation.detector_confidence,
                )
            )

        if progress_callback:
            progress_callback(
                ScanProgress(
                    filename=source_filename,
                    duration_seconds=metadata.duration_seconds,
                    current_seconds=sample.timestamp_seconds,
                    frames_processed=processed_samples,
                    detections_found=len(detections),
                    range_start_seconds=start_seconds,
                    range_end_seconds=end_seconds,
                    phase="Scanning and ranking text",
                )
            )

    tracking_interval = max(
        sample_interval_seconds,
        settings.dialogue_interval_seconds
        if caption_timeline is not None and settings.use_dialogue_optimization
        else sample_interval_seconds,
    )
    line_events = track_detections(
        detections,
        sample_interval_seconds=tracking_interval,
        config=TrackingConfig(max_gap_seconds=max(1.25, tracking_interval * 1.4)),
    )
    events = group_screen_text_moments(
        line_events,
        sample_interval_seconds=tracking_interval,
    )
    events = score_text_events(
        events,
        caption_timeline=caption_timeline,
        scene_change_times=scene_change_times,
        review_breadth=review_breadth,
    )
    save_cached_event_screenshots(
        events,
        output_dir / "screenshots",
        cached_frames,
        annotated=settings.save_annotated_screenshots,
    )
    remove_candidate_cache(candidate_cache_dir)

    report_csv = output_dir / "report.csv"
    report_html = output_dir / "report.html"
    raw_json = output_dir / "raw_detections.json"
    write_csv_report(report_csv, events)
    write_html_report(
        report_html,
        events=events,
        metadata=metadata,
        scan_mode=scan_mode,
        ocr_model=ocr_model,
        scan_start_seconds=start_seconds,
        scan_end_seconds=end_seconds,
        min_ocr_confidence=min_ocr_confidence,
        review_breadth=review_breadth,
        caption_path=caption_timeline.path if caption_timeline else None,
        dialogue_optimization=settings.use_dialogue_optimization and caption_timeline is not None,
        scene_detection=scene_detection_active,
    )
    write_raw_json(
        raw_json,
        detections=detections,
        events=events,
        metadata=metadata,
        scan_mode=scan_mode,
        ocr_model=ocr_model,
        scan_start_seconds=start_seconds,
        scan_end_seconds=end_seconds,
        min_ocr_confidence=min_ocr_confidence,
        review_breadth=review_breadth,
        caption_path=caption_timeline.path if caption_timeline else None,
        dialogue_optimization=settings.use_dialogue_optimization and caption_timeline is not None,
        scene_detection=scene_detection_active,
        scene_change_times=scene_change_times,
    )

    LOGGER.info("Scan complete events=%d detections=%d output=%s", len(events), len(detections), output_dir)
    return ScanResult(
        output_dir,
        metadata,
        scan_mode,
        detections,
        events,
        report_html,
        report_csv,
        raw_json,
        caption_timeline.path if caption_timeline else None,
    )


def validate_min_ocr_confidence(value: float) -> float:
    confidence = float(value)
    if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
        raise ValueError("Text strictness must be between 0% and 100%.")
    return confidence


def validate_review_breadth(value: float) -> float:
    breadth = float(value)
    if not math.isfinite(breadth) or not 0.0 <= breadth <= 1.0:
        raise ValueError("Review breadth must be between 0% and 100%.")
    return breadth


def filter_ocr_observations(
    observations: Iterable[OCRTextObservation],
    min_confidence: float,
) -> list[OCRTextObservation]:
    threshold = validate_min_ocr_confidence(min_confidence)
    return [
        observation
        for observation in observations
        if observation.text.strip() and observation.confidence >= threshold
    ]


def _should_tile(settings: ScanSettings, metadata: VideoMetadata, scan_mode: ScanMode) -> bool:
    value = settings.enable_uhd_tiling.lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    del metadata, scan_mode
    return False


def _load_caption_timeline(
    video_path: str | Path,
    settings: ScanSettings,
) -> CaptionTimeline | None:
    if not settings.use_dialogue_optimization:
        return None
    caption_path = Path(settings.caption_path) if settings.caption_path else find_sidecar_caption(video_path)
    if caption_path is None:
        return None
    return CaptionTimeline.from_file(caption_path)


def _resolve_scan_range(metadata: VideoMetadata, settings: ScanSettings) -> tuple[float, float | None]:
    start_seconds = max(0.0, settings.start_seconds or 0.0)
    end_seconds = settings.end_seconds

    if metadata.duration_seconds > 0:
        if start_seconds >= metadata.duration_seconds:
            raise ValueError("Start time is beyond the end of the video.")
        if end_seconds is None:
            end_seconds = metadata.duration_seconds
        else:
            end_seconds = min(end_seconds, metadata.duration_seconds)

    if end_seconds is not None and end_seconds <= start_seconds:
        raise ValueError("End time must be after start time.")

    return start_seconds, end_seconds
