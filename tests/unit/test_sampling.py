from __future__ import annotations

from fractions import Fraction

from find_that_text.video.sampling import estimated_sample_interval_seconds, resolve_scan_mode


def test_default_mode_checks_every_23_frames() -> None:
    mode = resolve_scan_mode("default")
    assert mode.name == "default"
    assert mode.frame_step == 23
    assert mode.description == "every 23 frames"


def test_advanced_mode_checks_every_frame() -> None:
    mode = resolve_scan_mode("advanced")
    assert mode.name == "advanced"
    assert mode.frame_step == 1
    assert mode.description == "every frame"


def test_frame_step_interval_uses_video_rate() -> None:
    mode = resolve_scan_mode("default")
    assert estimated_sample_interval_seconds(mode, Fraction(23, 1)) == 1.0
