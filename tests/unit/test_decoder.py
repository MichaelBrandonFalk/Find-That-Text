from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import json
import threading

import pytest

import av
import numpy as np

from find_that_text.video.decoder import iter_sampled_frames
from find_that_text.ocr.engine import EmptyOCREngine
from find_that_text.scanner import ScanCancelled, ScanProgress, ScanSettings, find_dialogue_gaps, scan_video


def _make_video(path: Path, *, seconds: int = 4, fps: int = 24, static: bool = False) -> None:
    with av.open(str(path), "w") as container:
        stream = container.add_stream("mpeg4", rate=fps)
        stream.width = 64
        stream.height = 48
        stream.pix_fmt = "yuv420p"
        stream.time_base = Fraction(1, fps)
        for index in range(seconds * fps):
            image = np.full((48, 64, 3), 40 if static else index % 256, dtype=np.uint8)
            frame = av.VideoFrame.from_ndarray(image, format="rgb24")
            frame.pts = index
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


def test_default_cadence_and_gap_filter_are_independent(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    _make_video(video)

    all_samples = list(iter_sampled_frames(video, frame_step=23))
    gap_samples = list(
        iter_sampled_frames(video, frame_step=23, sample_filter=lambda timestamp: not 1 <= timestamp < 3)
    )

    assert [sample.index for sample in all_samples] == [0, 23, 46, 69, 92]
    assert [sample.index for sample in gap_samples] == [0, 23, 92]


def test_late_range_seeks_to_start_and_keeps_frame_cadence(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    _make_video(video, seconds=8)

    samples = list(iter_sampled_frames(video, frame_step=23, start_seconds=6.0, end_seconds=7.5))

    assert len(samples) == 2
    assert abs(samples[0].timestamp_seconds - 6.0) < 0.01
    assert abs(samples[1].timestamp_seconds - (6 + 23 / 24)) < 0.01


def test_fastest_scan_uses_caption_gaps_and_can_scan_dialogue_too(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    captions = tmp_path / "clip.srt"
    _make_video(video)
    captions.write_text("1\n00:00:01,000 --> 00:00:03,000\nSpeaking\n", encoding="utf-8")

    progress = []
    fastest = scan_video(
        video,
        settings=ScanSettings(output_root=tmp_path / "fastest"),
        engine=EmptyOCREngine(),
        progress_callback=progress.append,
    )
    fastest_json = json.loads(fastest.raw_json.read_text(encoding="utf-8"))
    assert fastest.caption_path == captions
    assert fastest_json["scan"]["dialogue_gaps_only"] is True
    assert fastest_json["scan"]["frame_step"] == 23
    assert progress[-1].frames_processed == 2

    full = scan_video(
        video,
        settings=ScanSettings(output_root=tmp_path / "full", only_dialogue_gaps=False),
        engine=EmptyOCREngine(),
        progress_callback=progress.append,
    )
    full_json = json.loads(full.raw_json.read_text(encoding="utf-8"))
    assert full_json["scan"]["dialogue_gaps_only"] is False
    assert progress[-1].frames_processed == 5


def test_disabled_auto_caption_discovery_scans_full_video(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    captions = tmp_path / "clip.srt"
    _make_video(video)
    captions.write_text("1\n00:00:01,000 --> 00:00:03,000\nSpeaking\n", encoding="utf-8")
    progress = []

    result = scan_video(
        video,
        settings=ScanSettings(output_root=tmp_path / "reports", auto_find_captions=False),
        engine=EmptyOCREngine(),
        progress_callback=progress.append,
    )

    assert result.caption_path is None
    assert progress[-1].frames_processed == 5


def test_music_is_scanned_and_dialogue_gap_timeline_is_exported(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    captions = tmp_path / "clip.srt"
    _make_video(video)
    captions.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\nSpeaking\n\n"
        "2\n00:00:03,000 --> 00:00:04,000\n[MUSIC]\n",
        encoding="utf-8",
    )
    progress = []

    result = scan_video(
        video,
        settings=ScanSettings(output_root=tmp_path / "reports"),
        engine=EmptyOCREngine(),
        progress_callback=progress.append,
    )

    assert progress[-1].frames_processed == 2
    assert (result.output_dir / "dialogue_gaps.html").exists()
    assert result.shareable_html.exists()
    csv_text = (result.output_dir / "dialogue_gaps.csv").read_text(encoding="utf-8")
    assert "00:00:00.000,00:00:00.850" in csv_text
    assert "00:00:03.150" in csv_text
    assert 'href="dialogue_gaps.html"' in result.report_html.read_text(encoding="utf-8")


def test_super_speed_run_never_decodes_frames_or_loads_ocr(tmp_path: Path, monkeypatch) -> None:
    video = tmp_path / "clip.mp4"
    captions = tmp_path / "clip.srt"
    _make_video(video)
    captions.write_text("1\n00:00:01,000 --> 00:00:03,000\nSpeaking\n", encoding="utf-8")

    def unexpected_call(*args, **kwargs):
        raise AssertionError("Super Speed Run must not decode frames or run OCR")

    monkeypatch.setattr("find_that_text.scanner.iter_sampled_frames", unexpected_call)
    monkeypatch.setattr("find_that_text.scanner.PaddleOCREngine", unexpected_call)

    result = find_dialogue_gaps(video, settings=ScanSettings(output_root=tmp_path / "gaps"))

    assert len(result.gaps) == 2
    assert result.report_csv.exists()
    assert "data:text/csv;base64," in result.report_html.read_text(encoding="utf-8")
    assert "No video frames were decoded and no OCR was run." in result.report_html.read_text(encoding="utf-8")
    assert "1s</strong>minimum dialogue break" in result.report_html.read_text(encoding="utf-8")
    assert "elapsed processing time" in result.report_html.read_text(encoding="utf-8")
    assert result.elapsed_seconds >= 0


def test_super_speed_run_requires_captions(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    _make_video(video)

    with pytest.raises(ValueError, match="needs an English or Spanish SRT/VTT"):
        find_dialogue_gaps(video, settings=ScanSettings(output_root=tmp_path / "gaps"))


def test_short_gaps_skip_video_decode_entirely(tmp_path: Path, monkeypatch) -> None:
    video = tmp_path / "clip.mp4"
    captions = tmp_path / "clip.srt"
    _make_video(video, seconds=4)
    captions.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nHello\n\n"
        "2\n00:00:01,500 --> 00:00:04,000\nWorld\n",
        encoding="utf-8",
    )

    def unexpected_decode(*args, **kwargs):
        raise AssertionError("No eligible gap should bypass video decoding")

    monkeypatch.setattr("find_that_text.scanner.iter_sampled_frames", unexpected_decode)
    result = scan_video(video, settings=ScanSettings(output_root=tmp_path / "reports"), engine=EmptyOCREngine())

    assert result.events == []
    assert result.report_xlsx.is_file()
    assert result.elapsed_seconds >= 0
    scan = json.loads(result.raw_json.read_text(encoding="utf-8"))["scan"]
    assert scan["minimum_dialogue_gap_seconds"] == 1.0
    assert scan["elapsed_seconds"] >= 0
    assert "Scan Time" in result.report_html.read_text(encoding="utf-8")


def test_eligible_one_second_gap_gets_a_midpoint_sample(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    captions = tmp_path / "clip.srt"
    _make_video(video, seconds=4)
    captions.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nHello\n\n"
        "2\n00:00:02,000 --> 00:00:04,000\nWorld\n",
        encoding="utf-8",
    )
    progress = []

    result = scan_video(
        video,
        settings=ScanSettings(output_root=tmp_path / "reports"),
        engine=EmptyOCREngine(),
        progress_callback=progress.append,
    )

    assert progress[-1].frames_processed == 1
    assert 1.5 <= progress[-1].current_seconds < 1.6
    assert "00:00:01.150,00:00:01.850" in (
        result.output_dir / "dialogue_gaps.csv"
    ).read_text(encoding="utf-8")


def test_gap_only_scan_reports_progress_and_can_cancel_without_samples(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    captions = tmp_path / "clip.srt"
    _make_video(video, seconds=8)
    captions.write_text("1\n00:00:00,000 --> 00:00:08,000\nSpeaking\n", encoding="utf-8")
    cancel_event = threading.Event()
    progress = []

    def on_progress(update: ScanProgress) -> None:
        progress.append(update)
        if update.current_seconds >= 5.0:
            cancel_event.set()

    with pytest.raises(ScanCancelled):
        scan_video(
            video,
            settings=ScanSettings(output_root=tmp_path / "reports"),
            engine=EmptyOCREngine(),
            progress_callback=on_progress,
            cancel_event=cancel_event,
        )

    assert progress[-1].frames_processed == 0
    assert progress[-1].current_seconds >= 5.0


def test_static_sampled_frames_reuse_ocr_without_changing_sample_count(tmp_path: Path) -> None:
    video = tmp_path / "static.mp4"
    _make_video(video, static=True)
    progress = []
    result = scan_video(
        video,
        settings=ScanSettings(output_root=tmp_path / "reports", auto_find_captions=False),
        engine=EmptyOCREngine(),
        progress_callback=progress.append,
    )
    scan = json.loads(result.raw_json.read_text(encoding="utf-8"))["scan"]

    assert progress[-1].frames_processed == 5
    assert scan["ocr_frames_analyzed"] == 2
    assert scan["ocr_frames_reused"] == 3
