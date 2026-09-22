from __future__ import annotations

from pathlib import Path

from find_that_text.captions import CaptionTimeline, find_sidecar_caption


def test_srt_timeline_tracks_dialogue_and_quiet_gaps(tmp_path: Path) -> None:
    path = tmp_path / "movie.en.srt"
    path.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\nHello\n\n"
        "2\n00:00:05,000 --> 00:00:07,000\nWorld\n",
        encoding="utf-8",
    )

    timeline = CaptionTimeline.from_file(path)

    assert timeline.is_dialogue_active(2.0)
    assert not timeline.is_dialogue_active(4.0)
    assert timeline.quiet_gap_starts(end_seconds=10.0) == [3.05, 7.05]


def test_vtt_timeline_accepts_minute_timestamps(tmp_path: Path) -> None:
    path = tmp_path / "movie.es.vtt"
    path.write_text("WEBVTT\n\n00:01.000 --> 00:02.500 align:start\nHola\n", encoding="utf-8")

    timeline = CaptionTimeline.from_file(path)

    assert timeline.is_dialogue_active(1.5)
    assert not timeline.is_dialogue_active(4.0)


def test_sidecar_prefers_english_or_spanish_named_caption(tmp_path: Path) -> None:
    video = tmp_path / "Feature.mov"
    video.touch()
    (tmp_path / "Feature.notes.vtt").touch()
    spanish = tmp_path / "Feature.es.srt"
    spanish.touch()

    assert find_sidecar_caption(video) == spanish
