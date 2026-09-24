from __future__ import annotations

import sys

from find_that_text.gui.main_window import run
from find_that_text.util.app_dirs import configure_paddle_cache
from find_that_text.version import __version__


def main() -> int:
    if "--self-test-gui" in sys.argv:
        from PySide6.QtWidgets import QApplication

        from find_that_text.gui.main_window import MainWindow

        app = QApplication([])
        window = MainWindow()
        window.show()
        app.processEvents()
        window.close()
        return 0
    if "--self-test" in sys.argv or "--self-test-ocr" in sys.argv:
        configure_paddle_cache()
        import av
        import onnxruntime
        import paddle
        import paddleocr
        import PySide6

        from find_that_text.ocr.engine import PaddleOCREngine

        if sys.stdout is not None:
            print(f"Find That Text {__version__}")
            print(f"paddle {paddle.__version__}")
            print(f"paddleocr {PaddleOCREngine.version}")
            print(f"av {av.__version__}")
            print(f"onnxruntime {onnxruntime.__version__}")
            print(f"pyside6 {PySide6.__version__}")
        if "--self-test-ocr" in sys.argv:
            import numpy as np
            from PIL import Image, ImageDraw

            image = Image.new("RGB", (640, 360), (20, 24, 32))
            draw = ImageDraw.Draw(image)
            draw.text((80, 150), "HELLO WORLD", fill=(255, 255, 255))
            engine = PaddleOCREngine()
            observations = engine.recognize(np.array(image))
            if not observations:
                raise RuntimeError("Bundled OCR models returned no text in the self-test")
            if sys.stdout is not None:
                print(f"ocr observations {len(observations)}")
                for observation in observations:
                    print(f"{observation.confidence:.3f} {observation.text}")
        return 0
    return run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
