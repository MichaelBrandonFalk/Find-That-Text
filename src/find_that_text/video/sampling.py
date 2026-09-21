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


def resolve_scan_mode(mode: str, custom_interval: float | None = None) -> ScanMode:
    key = mode.lower().strip()
    if key in {"default", "standard"}:
        return ScanMode("default", frame_step=SCAN_MODE_FRAME_STEPS["default"])
    if key in {"advanced", "every-frame", "every_frame", "thorough"}:
        return ScanMode("advanced", frame_step=SCAN_MODE_FRAME_STEPS["advanced"])
    if key == "custom":
        if custom_interval is None or custom_interval <= 0:
            raise ValueError("Custom scan mode requires a positive interval.")
        return ScanMode("custom", custom_interval)
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
