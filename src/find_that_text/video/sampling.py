from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


SCAN_MODE_FRAME_STEPS = {
    "default": 23,
    "advanced": 1,
}

LEGACY_SCAN_MODE_INTERVALS = {
    "fast": 1.0,
    "standard": 0.5,
    "thorough": 0.25,
}


@dataclass(frozen=True, slots=True)
class ScanMode:
    name: str
    interval_seconds: float | None = None
    frame_step: int | None = None

    @property
    def description(self) -> str:
        if self.frame_step == 1:
            return "every frame"
        if self.frame_step:
            return f"every {self.frame_step} frames"
        if self.interval_seconds:
            return f"every {self.interval_seconds:.2f}s"
        return "custom"


def resolve_scan_mode(
    mode: str,
    custom_frame_step: int | None = None,
    custom_interval_seconds: float | None = None,
) -> ScanMode:
    key = mode.lower().strip()
    if key == "default":
        return ScanMode("default", frame_step=SCAN_MODE_FRAME_STEPS["default"])
    if key in {"adaptive", "standard"}:
        return ScanMode("adaptive", interval_seconds=1.0)
    if key in {"advanced", "every-frame", "every_frame", "thorough"}:
        return ScanMode("advanced", frame_step=SCAN_MODE_FRAME_STEPS["advanced"])
    if key == "custom":
        if custom_frame_step is not None:
            if (
                isinstance(custom_frame_step, bool)
                or not isinstance(custom_frame_step, int)
                or custom_frame_step <= 0
            ):
                raise ValueError("Custom frame interval must be a positive whole number.")
            return ScanMode("custom", frame_step=custom_frame_step)
        if custom_interval_seconds is not None and custom_interval_seconds > 0:
            return ScanMode("custom", interval_seconds=custom_interval_seconds)
        raise ValueError("Custom scan mode requires a positive frame interval.")
    if key not in LEGACY_SCAN_MODE_INTERVALS:
        raise ValueError(f"Unknown scan mode: {mode}")
    return ScanMode(key, LEGACY_SCAN_MODE_INTERVALS[key])


def estimated_sample_interval_seconds(scan_mode: ScanMode, average_rate: Fraction | None) -> float:
    if scan_mode.interval_seconds is not None:
        return scan_mode.interval_seconds
    if scan_mode.frame_step is not None and average_rate:
        fps = float(average_rate)
        if fps > 0:
            return scan_mode.frame_step / fps
    return 0.5
