from __future__ import annotations

from pathlib import Path

import pytest

from find_that_text.captions import CaptionCue, CaptionTimeline, find_sidecar_caption


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


def test_music_and_sound_cues_are_scan_time_but_mixed_speech_is_not(tmp_path: Path) -> None:
    path = tmp_path / "movie.es.srt"
    path.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\n[MUSIC]\n\n"
        "2\n00:00:01,000 --> 00:00:02,000\n♪ la la ♪\n\n"
        "3\n00:00:02,000 --> 00:00:03,000\n(door slams)\n\n"
        "4\n00:00:03,000 --> 00:00:04,000\nMusic is my life.\n\n"
        "5\n00:00:04,000 --> 00:00:05,000\n[applause] Hola.\n\n"
        "6\n00:00:05,000 --> 00:00:06,000\n<v Announcer>Welcome!</v>\n",
        encoding="utf-8",
    )

    timeline = CaptionTimeline.from_file(path)

    assert timeline.total_cue_count == 6
    assert timeline.non_dialogue_cue_count == 3
    assert not timeline.is_dialogue_active(0.5)
    assert not timeline.is_dialogue_active(1.5)
    assert not timeline.is_dialogue_active(2.5)
    assert timeline.is_dialogue_active(3.5)
    assert timeline.is_dialogue_active(4.5)
    assert timeline.is_dialogue_active(5.5)
    assert [(gap.start_seconds, gap.end_seconds) for gap in timeline.dialogue_gaps(
        start_seconds=0.0, end_seconds=6.0
    )] == [(0.0, 2.85)]


def test_music_only_captions_leave_full_scan_range_and_vtt_note_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "movie.vtt"
    path.write_text(
        "WEBVTT\n\n"
        "NOTE\n00:00:00.000 --> 00:00:10.000\nIgnore this example\n\n"
        "00:00:01.000 --> 00:00:04.000\n<i>[Música]</i>\n",
        encoding="utf-8",
    )

    timeline = CaptionTimeline.from_file(path)

    assert timeline.total_cue_count == 1
    assert timeline.non_dialogue_cue_count == 1
    assert timeline.dialogue_gaps(start_seconds=2.0, end_seconds=5.0) == [CaptionCue(2.0, 5.0)]


def test_minimum_dialogue_gap_uses_raw_break_before_speech_padding(tmp_path: Path) -> None:
    path = tmp_path / "movie.srt"
    path.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nHello\n\n"
        "2\n00:00:01,500 --> 00:00:02,500\nHello\n\n"
        "3\n00:00:03,500 --> 00:00:04,500\nHello\n\n"
        "4\n00:00:06,500 --> 00:00:07,000\nHello\n",
        encoding="utf-8",
    )
    timeline = CaptionTimeline.from_file(path)

    assert timeline.dialogue_gaps(start_seconds=0, end_seconds=8, minimum_gap_seconds=1.0) == [
        CaptionCue(2.65, 3.35),
        CaptionCue(4.65, 6.35),
        CaptionCue(7.15, 8),
    ]
    assert timeline.dialogue_gaps(start_seconds=0, end_seconds=8, minimum_gap_seconds=2.0) == [
        CaptionCue(4.65, 6.35)
    ]
    assert CaptionCue(1.15, 1.35) in timeline.dialogue_gaps(
        start_seconds=0, end_seconds=8, minimum_gap_seconds=0.5
    )
    with pytest.raises(ValueError, match="Minimum dialogue gap"):
        timeline.dialogue_gaps(start_seconds=0, end_seconds=8, minimum_gap_seconds=float("nan"))
