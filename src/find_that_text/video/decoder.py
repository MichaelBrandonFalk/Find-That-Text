from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator

import numpy as np


@dataclass(slots=True)
class FrameSample:
    index: int
    timestamp_seconds: float
    width: int
    height: int
    image_rgb: np.ndarray


def iter_sampled_frames(
    path: str | Path,
    interval_seconds: float | None = None,
    *,
    frame_step: int | None = None,
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
    priority_timestamps: Iterable[float] | None = None,
    interval_selector: Callable[[float], float] | None = None,
    max_dimension: int | None = None,
) -> Iterator[FrameSample]:
    try:
        import av
    except ImportError as exc:  # pragma: no cover - exercised in dependency spike
        raise RuntimeError("PyAV is required for video decoding. Install the pinned runtime.") from exc

    if frame_step is None and interval_seconds is None:
        raise ValueError("Either frame_step or interval_seconds is required.")
    if frame_step is not None and frame_step <= 0:
        raise ValueError("frame_step must be greater than zero.")
    if interval_seconds is not None and interval_seconds <= 0:
        raise ValueError("interval_seconds must be greater than zero.")

    next_sample_time = max(0.0, start_seconds)
    priority_times = sorted(
        timestamp
        for timestamp in (priority_timestamps or [])
        if timestamp >= start_seconds and (end_seconds is None or timestamp <= end_seconds)
    )
    priority_index = 0
    decoded_index = -1
    range_frame_index = 0
    with av.open(str(path)) as container:
        streams = [stream for stream in container.streams.video]
        if not streams:
            raise ValueError(f"No video stream found in {path}")
        stream = streams[0]
        for frame in container.decode(stream):
            decoded_index += 1
            timestamp = frame.time
            if timestamp is None:
                if frame.pts is None or frame.time_base is None:
                    continue
                timestamp = float(frame.pts * frame.time_base)
            if timestamp + 1e-6 < start_seconds:
                continue
            if end_seconds is not None and timestamp > end_seconds:
                break
            priority_due = (
                priority_index < len(priority_times)
                and timestamp + 1e-6 >= priority_times[priority_index]
            )
            if frame_step is not None:
                regular_due = range_frame_index % frame_step == 0
                range_frame_index += 1
                if not regular_due and not priority_due:
                    continue
            elif interval_seconds is not None:
                regular_due = timestamp + 1e-6 >= next_sample_time
                if not regular_due and not priority_due:
                    continue

            while priority_index < len(priority_times) and priority_times[priority_index] <= timestamp + 1e-6:
                priority_index += 1

            converted_frame = frame
            if max_dimension and max(frame.width, frame.height) > max_dimension:
                scale = max_dimension / max(frame.width, frame.height)
                converted_frame = frame.reformat(
                    width=max(1, round(frame.width * scale)),
                    height=max(1, round(frame.height * scale)),
                    format="rgb24",
                )
            image = converted_frame.to_ndarray(format="rgb24")
            yield FrameSample(
                index=decoded_index,
                timestamp_seconds=float(timestamp),
                width=int(image.shape[1]),
                height=int(image.shape[0]),
                image_rgb=image,
            )
            if interval_seconds is not None and regular_due:
                selected_interval = (
                    interval_selector(float(timestamp)) if interval_selector else interval_seconds
                )
                if selected_interval <= 0:
                    raise ValueError("Adaptive sample interval must be greater than zero.")
                next_sample_time = float(timestamp) + selected_interval
