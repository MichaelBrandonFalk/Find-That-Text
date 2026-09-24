from __future__ import annotations

import os
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory

import av
import numpy as np


def make_test_video(path: Path) -> None:
    with av.open(str(path), "w") as container:
        stream = container.add_stream("mpeg4", rate=24)
        stream.width = 320
        stream.height = 180
        stream.pix_fmt = "yuv420p"
        stream.time_base = Fraction(1, 24)
        image = np.full((180, 320, 3), 40, dtype=np.uint8)
        image[60:90, 45:275] = 230
        for index in range(48):
            frame = av.VideoFrame.from_ndarray(image, format="rgb24")
            frame.pts = index
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


def main() -> int:
    bundle = Path(sys.argv[1]).resolve()
    executable = bundle / "Find That Text.exe"
    if not executable.is_file():
        raise FileNotFoundError(executable)
    for library_name in ("mklml.dll", "libiomp5md.dll"):
        library = bundle / "_internal" / "paddle" / "libs" / library_name
        if not library.is_file():
            raise FileNotFoundError(f"Bundled Paddle library missing: {library}")
    for model_name in ("PP-OCRv6_small_det", "PP-OCRv6_small_rec"):
        model_dir = bundle / "_internal" / "PaddleX" / "official_models" / model_name
        if not model_dir.is_dir() or not any(model_dir.iterdir()):
            raise FileNotFoundError(f"Bundled OCR model missing: {model_dir}")

    with TemporaryDirectory(prefix="find-that-text-windows-test-") as temp_dir:
        video_path = Path(temp_dir) / "test.mp4"
        make_test_video(video_path)
        video_path.with_suffix(".srt").write_text(
            "1\n00:00:00,000 --> 00:00:00,200\nSpeaking\n", encoding="utf-8"
        )
        env = os.environ.copy()
        env.pop("PADDLE_PDX_CACHE_HOME", None)
        env["FIND_THAT_TEXT_APP_SUPPORT"] = temp_dir
        log_path = Path(temp_dir) / "self-test.log"
        env["FIND_THAT_TEXT_SELF_TEST_LOG"] = str(log_path)
        for arguments in (
            ("--self-test",),
            ("--self-test-gui",),
            ("--self-test-ocr",),
            ("--self-test-scan", str(video_path)),
        ):
            print(f"Running packaged {arguments[0]}", flush=True)
            try:
                result = subprocess.run([str(executable), *arguments], env=env, timeout=300, check=False)
            except subprocess.TimeoutExpired as exc:
                details = log_path.read_text(encoding="utf-8") if log_path.exists() else "No test log"
                raise RuntimeError(f"Packaged {arguments[0]} timed out.\n{details}") from exc
            if result.returncode != 0:
                details = log_path.read_text(encoding="utf-8") if log_path.exists() else "No test log"
                raise RuntimeError(
                    f"Packaged {arguments[0]} failed with exit code {result.returncode}.\n{details}"
                )
        for model_name in ("PP-OCRv6_small_det", "PP-OCRv6_small_rec"):
            model_dir = Path(temp_dir) / "PaddleX" / "official_models" / model_name
            if not model_dir.is_dir() or not any(model_dir.iterdir()):
                raise FileNotFoundError(f"Bundled model was not installed: {model_dir}")
    print("Extracted Windows bundle passed import, GUI, OCR, and report checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
