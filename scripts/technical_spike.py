from __future__ import annotations

import argparse
import importlib.util
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from find_that_text.ocr.engine import PaddleOCREngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OCR/video packaging spike checks.")
    parser.add_argument("--backend", default=None, choices=[None, "paddle_static", "onnxruntime"])
    parser.add_argument("--sizes", nargs="*", default=["1920x1080", "3840x2160"])
    args = parser.parse_args()

    for module in ["paddle", "paddleocr", "av", "PySide6"]:
        print(f"{module}: {'ok' if importlib.util.find_spec(module) else 'missing'}")

    engine = PaddleOCREngine(engine=args.backend)
    for size in args.sizes:
        width, height = [int(part) for part in size.lower().split("x", 1)]
        frame = synthetic_frame(width, height)
        started = time.perf_counter()
        observations = engine.recognize(np.array(frame))
        elapsed = time.perf_counter() - started
        print(f"{size}: {len(observations)} observations in {elapsed:.2f}s")
        for observation in observations[:10]:
            print(f"  {observation.confidence:.3f} {observation.text!r} {observation.box}")
    return 0


def synthetic_frame(width: int, height: int) -> Image.Image:
    image = Image.new("RGB", (width, height), (32, 36, 42))
    draw = ImageDraw.Draw(image)
    draw.rectangle((60, 60, width - 60, height - 60), outline=(90, 100, 110), width=3)
    draw.text((width * 0.12, height * 0.22), "HELLO WORLD", fill=(255, 255, 255))
    draw.text((width * 0.08, height * 0.78), "ATLANTA, GEORGIA", fill=(255, 240, 128))
    draw.text((width * 0.72, height * 0.06), "PURE FLIX", fill=(220, 220, 220))
    draw.text((width * 0.50, height * 0.50), "small phone text 12:45", fill=(180, 220, 255))
    return image


if __name__ == "__main__":
    raise SystemExit(main())
