from __future__ import annotations

import sys

from find_that_text.gui.main_window import run
from find_that_text.util.app_dirs import configure_paddle_cache
from find_that_text.version import __version__


def main() -> int:
    if "--self-test" in sys.argv or "--self-test-ocr" in sys.argv:
        configure_paddle_cache()
        import av
        import onnxruntime
        import paddle
        import paddleocr
        import PySide6

        print(f"Find That Text {__version__}")
        print(f"paddle {paddle.__version__}")
        print(f"paddleocr {getattr(paddleocr, '__version__', 'unknown')}")
        print(f"av {av.__version__}")
        print(f"onnxruntime {onnxruntime.__version__}")
        print(f"pyside6 {PySide6.__version__}")
        if "--self-test-ocr" in sys.argv:
            import numpy as np
            from PIL import Image, ImageDraw

            from find_that_text.ocr.engine import PaddleOCREngine

            image = Image.new("RGB", (640, 360), (20, 24, 32))
            draw = ImageDraw.Draw(image)
            draw.text((80, 150), "HELLO WORLD", fill=(255, 255, 255))
            engine = PaddleOCREngine()
            observations = engine.recognize(np.array(image))
            print(f"ocr observations {len(observations)}")
            for observation in observations:
                print(f"{observation.confidence:.3f} {observation.text}")
        return 0
    return run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
