from __future__ import annotations

import numpy as np

from find_that_text.ocr.engine import OCRTextObservation
from find_that_text.ocr.reuse import OCRReuseCache


def _observation(text: str) -> OCRTextObservation:
    return OCRTextObservation(
        text=text,
        confidence=0.95,
        polygon=[[2, 2], [20, 2], [20, 10], [2, 10]],
        box=(2, 2, 18, 8),
    )


def test_reuses_near_identical_frames_but_forces_regular_ocr() -> None:
    cache = OCRReuseCache()
    image = np.full((64, 64, 3), 40, dtype=np.uint8)
    calls = []

    def recognize(frame: np.ndarray) -> list[OCRTextObservation]:
        calls.append(frame)
        return [_observation("TITLE")]

    assert cache.recognize(image, recognize)[0].text == "TITLE"
    image_with_noise = image.copy()
    image_with_noise[0, 0] = [43, 42, 41]
    assert cache.recognize(image_with_noise, recognize)[0].text == "TITLE"
    assert cache.recognize(image_with_noise, recognize)[0].text == "TITLE"
    assert cache.recognize(image_with_noise, recognize)[0].text == "TITLE"

    assert len(calls) == 2
    assert cache.ocr_frames == 2
    assert cache.reused_frames == 2


def test_small_local_text_change_triggers_fresh_ocr() -> None:
    cache = OCRReuseCache()
    image = np.full((64, 64, 3), 40, dtype=np.uint8)
    changed = image.copy()
    changed[5:8, 5:8] = 240
    calls = 0

    def recognize(frame: np.ndarray) -> list[OCRTextObservation]:
        nonlocal calls
        calls += 1
        return [_observation("NEW" if frame[5, 5, 0] > 100 else "OLD")]

    assert cache.recognize(image, recognize)[0].text == "OLD"
    assert cache.recognize(changed, recognize)[0].text == "NEW"
    assert calls == 2
    assert cache.reused_frames == 0


def test_size_change_always_triggers_fresh_ocr() -> None:
    cache = OCRReuseCache()
    calls = 0

    def recognize(frame: np.ndarray) -> list[OCRTextObservation]:
        nonlocal calls
        calls += 1
        return []

    cache.recognize(np.zeros((64, 64, 3), dtype=np.uint8), recognize)
    cache.recognize(np.zeros((65, 64, 3), dtype=np.uint8), recognize)
    assert calls == 2
