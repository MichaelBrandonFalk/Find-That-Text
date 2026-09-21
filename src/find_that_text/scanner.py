from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from find_that_text.ocr.engine import OCREngine, PaddleOCREngine
from find_that_text.ocr.tiling import recognize_with_optional_tiling
from find_that_text.reports.csv_report import write_csv_report
from find_that_text.reports.html_report import write_html_report
from find_that_text.reports.raw_json import write_raw_json
from find_that_text.reports.screenshots import save_event_screenshots
from find_that_text.tracking.events import OCRDetection, TextEvent
from find_that_text.tracking.matcher import track_detections
from find_that_text.util.logging import configure_logging
from find_that_text.util.paths import create_output_dir
from find_that_text.video.decoder import iter_sampled_frames
from find_that_text.video.metadata import VideoMetadata, read_video_metadata
from find_that_text.video.sampling import ScanMode, estimated_sample_interval_seconds, resolve_scan_mode

LOGGER = logging.getLogger(__name__)


class ScanCancelled(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ScanSettings:
    mode: str = "default"
    custom_interval_seconds: float | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
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
    scan_mode = resolve_scan_mode(settings.mode, settings.custom_interval_seconds)
    metadata = read_video_metadata(video_path)
    start_seconds, end_seconds = _resolve_scan_range(metadata, settings)
    sample_interval_seconds = estimated_sample_interval_seconds(scan_mode, metadata.average_rate)
    output_dir = create_output_dir(video_path, settings.output_root)
    configure_logging(output_dir)

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

    ocr_engine = engine or PaddleOCREngine(engine=settings.ocr_backend, lang=settings.lang)
    ocr_model = getattr(ocr_engine, "model_description", getattr(ocr_engine, "name", "OCR"))
    detections: list[OCRDetection] = []
    source_filename = Path(video_path).name
    tiling_enabled = _should_tile(settings, metadata, scan_mode)
    processed_samples = 0

    for sample in iter_sampled_frames(
        video_path,
        interval_seconds=scan_mode.interval_seconds,
        frame_step=scan_mode.frame_step,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
    ):
        if cancel_event and cancel_event.is_set():
            LOGGER.info("Scan cancelled by user.")
            raise ScanCancelled("Scan cancelled.")

        processed_samples += 1
        observations = recognize_with_optional_tiling(
            ocr_engine,
            sample.image_rgb,
            enable_tiling=tiling_enabled,
        )
        for observation in observations:
            if not observation.text.strip():
                continue
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
                )
            )

    events = track_detections(detections, sample_interval_seconds=sample_interval_seconds)
    save_event_screenshots(
        video_path,
        events,
        output_dir / "screenshots",
        annotated=settings.save_annotated_screenshots,
    )

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
    )

    LOGGER.info("Scan complete events=%d detections=%d output=%s", len(events), len(detections), output_dir)
    return ScanResult(output_dir, metadata, scan_mode, detections, events, report_html, report_csv, raw_json)


def _should_tile(settings: ScanSettings, metadata: VideoMetadata, scan_mode: ScanMode) -> bool:
    value = settings.enable_uhd_tiling.lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return metadata.width >= 3200 or metadata.height >= 1800


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
