from __future__ import annotations

from find_that_text.cli import build_parser


def test_cli_exposes_minimum_gap_for_both_run_types() -> None:
    parser = build_parser()

    scan = parser.parse_args(["scan", "movie.mp4", "--minimum-gap-seconds", "0.5"])
    gaps = parser.parse_args(["gaps", "movie.mp4", "--minimum-gap-seconds", "3"])

    assert scan.minimum_gap_seconds == 0.5
    assert gaps.minimum_gap_seconds == 3.0
    assert parser.parse_args(["scan", "movie.mp4"]).minimum_gap_seconds == 1.0
