from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw

from find_that_text.video.decoder import iter_sampled_frames
from find_that_text.video.metadata import read_video_metadata


def main() -> int:
    out_dir = Path(".spike")
    out_dir.mkdir(exist_ok=True)
    mov_path = out_dir / "timestamp_fixture.mov"
    prores_path = out_dir / "timestamp_fixture_prores.mov"

    write_fixture(mov_path, codec="mpeg4", pix_fmt="yuv420p")
    print_result(mov_path)

    try:
        write_fixture(prores_path, codec="prores_ks", pix_fmt="yuv422p10le")
    except Exception as exc:
        print(f"ProRes encode skipped: {exc}")
    else:
        print_result(prores_path)
    return 0


def write_fixture(path: Path, *, codec: str, pix_fmt: str) -> None:
    width, height, fps, frames = 320, 180, 30, 90
    with av.open(str(path), "w") as container:
        stream = container.add_stream(codec, rate=fps)
        stream.width = width
        stream.height = height
        stream.pix_fmt = pix_fmt
        stream.time_base = Fraction(1, fps)
        for index in range(frames):
            image = Image.new("RGB", (width, height), (20, 24, 32))
            draw = ImageDraw.Draw(image)
            label = f"T={index / fps:0.3f}"
            draw.text((40, 76), label, fill=(255, 255, 255))
            frame = av.VideoFrame.from_ndarray(np.array(image), format="rgb24")
            frame.pts = index
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


def print_result(path: Path) -> None:
    metadata = read_video_metadata(path)
    samples = list(iter_sampled_frames(path, 0.5))
    timestamps = [round(sample.timestamp_seconds, 3) for sample in samples[:8]]
    print(
        f"{path.name}: codec={metadata.codec_name} "
        f"duration={metadata.duration_seconds:.3f} "
        f"resolution={metadata.width}x{metadata.height} "
        f"samples={timestamps}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
