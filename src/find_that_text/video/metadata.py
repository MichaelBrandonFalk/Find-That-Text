from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    path: Path
    filename: str
    duration_seconds: float
    width: int
    height: int
    average_rate: Fraction | None
    codec_name: str | None
    frame_count: int | None


def read_video_metadata(path: str | Path) -> VideoMetadata:
    try:
        import av
    except ImportError as exc:  # pragma: no cover - exercised in dependency spike
        raise RuntimeError("PyAV is required for video decoding. Install the pinned runtime.") from exc

    video_path = Path(path)
    with av.open(str(video_path)) as container:
        streams = [stream for stream in container.streams.video]
        if not streams:
            raise ValueError(f"No video stream found in {video_path}")
        stream = streams[0]
        duration = 0.0
        if stream.duration and stream.time_base:
            duration = float(stream.duration * stream.time_base)
        elif container.duration:
            duration = float(container.duration / av.time_base)
        return VideoMetadata(
            path=video_path,
            filename=video_path.name,
            duration_seconds=duration,
            width=int(stream.codec_context.width or 0),
            height=int(stream.codec_context.height or 0),
            average_rate=stream.average_rate,
            codec_name=stream.codec_context.name,
            frame_count=int(stream.frames) if stream.frames else None,
        )
