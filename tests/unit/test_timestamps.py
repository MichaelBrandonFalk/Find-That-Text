from __future__ import annotations

from find_that_text.util.timestamps import format_timestamp, parse_timestamp


def test_format_timestamp_uses_milliseconds() -> None:
    assert format_timestamp(271.5) == "00:04:31.500"
    assert format_timestamp(3661.2345) == "01:01:01.234"


def test_parse_timestamp_round_trips() -> None:
    assert parse_timestamp("00:04:31.500") == 271.5


def test_parse_timestamp_accepts_video_friendly_formats() -> None:
    assert parse_timestamp("00:30:30") == 1830.0
    assert parse_timestamp("30:30") == 1830.0
    assert parse_timestamp("90.5") == 90.5
