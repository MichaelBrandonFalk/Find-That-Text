from __future__ import annotations

import argparse
import sys
from pathlib import Path

from find_that_text.ocr.engine import EmptyOCREngine
from find_that_text.scanner import ScanCancelled, ScanProgress, ScanSettings, scan_video
from find_that_text.util.timestamps import format_timestamp, parse_timestamp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="find-that-text")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Scan a video for visible text.")
    scan.add_argument("video", type=Path, help="Path to MOV, MP4, or M4V video.")
    scan.add_argument(
        "--mode",
        choices=["default", "advanced", "custom", "standard", "fast", "thorough"],
        default="default",
        help="default checks every 23 frames; advanced checks every frame.",
    )
    custom = scan.add_mutually_exclusive_group()
    custom.add_argument(
        "--custom-frame-step",
        type=int,
        default=None,
        help="For custom mode, check every Nth frame.",
    )
    custom.add_argument(
        "--custom-interval",
        type=float,
        default=None,
        help="Legacy custom interval in seconds.",
    )
    scan.add_argument(
        "--min-confidence",
        type=float,
        default=0.5,
        help="Keep OCR results at or above this confidence from 0.0 to 1.0.",
    )
    scan.add_argument("--start", type=parse_timestamp, default=None, help="Start timestamp, for example 00:00:00.")
    scan.add_argument("--end", type=parse_timestamp, default=None, help="End timestamp, for example 00:30:30.")
    scan.add_argument("--output", type=Path, default=None, help="Output root folder.")
    scan.add_argument("--save-annotated-screenshots", action="store_true")
    scan.add_argument("--ocr-backend", choices=["paddle", "paddle_static", "paddle_dynamic", "onnxruntime"], default=None)
    scan.add_argument("--lang", default=None, help="PaddleOCR language code.")
    scan.add_argument("--uhd-tiling", choices=["auto", "on", "off"], default="auto")
    scan.add_argument(
        "--dry-run-empty-ocr",
        action="store_true",
        help="Exercise video/report plumbing without loading PaddleOCR.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "scan":
        settings = ScanSettings(
            mode=args.mode,
            custom_frame_step=args.custom_frame_step,
            custom_interval_seconds=args.custom_interval,
            min_ocr_confidence=args.min_confidence,
            start_seconds=args.start,
            end_seconds=args.end,
            output_root=args.output,
            save_annotated_screenshots=args.save_annotated_screenshots,
            ocr_backend=None if args.ocr_backend == "paddle" else args.ocr_backend,
            lang=args.lang,
            enable_uhd_tiling=args.uhd_tiling,
        )
        engine = EmptyOCREngine() if args.dry_run_empty_ocr else None
        try:
            result = scan_video(
                args.video,
                settings=settings,
                engine=engine,
                progress_callback=_print_progress,
            )
        except ScanCancelled:
            print("Scan cancelled.", file=sys.stderr)
            return 130
        print()
        print(f"Report folder: {result.output_dir}")
        print(f"HTML report:   {result.report_html}")
        print(f"CSV report:    {result.report_csv}")
        print(f"Raw JSON:      {result.raw_json}")
        print(f"Events:        {len(result.events)}")
        return 0
    return 2


def _print_progress(progress: ScanProgress) -> None:
    percent = progress.fraction * 100
    sys.stdout.write(
        "\r"
        f"{percent:5.1f}% "
        f"{format_timestamp(progress.current_seconds)} / {format_timestamp(progress.scan_end_seconds)} "
        f"frames={progress.frames_processed} detections={progress.detections_found}"
    )
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
