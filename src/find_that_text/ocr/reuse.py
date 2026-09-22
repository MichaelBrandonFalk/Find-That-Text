from __future__ import annotations

from collections.abc import Callable

import numpy as np

from find_that_text.ocr.engine import OCRTextObservation


class OCRReuseCache:
    def __init__(self, *, max_consecutive_reuses: int = 2) -> None:
        self.max_consecutive_reuses = max_consecutive_reuses
        self.ocr_frames = 0
        self.reused_frames = 0
        self._consecutive_reuses = 0
        self._last_image: np.ndarray | None = None
        self._last_observations: list[OCRTextObservation] = []

    def recognize(
        self,
        image_rgb: np.ndarray,
        recognize_frame: Callable[[np.ndarray], list[OCRTextObservation]],
    ) -> list[OCRTextObservation]:
        if (
            self._last_image is not None
            and self._consecutive_reuses < self.max_consecutive_reuses
            and _nearly_identical(self._last_image, image_rgb)
        ):
            self._consecutive_reuses += 1
            self.reused_frames += 1
            return self._last_observations

        observations = recognize_frame(image_rgb)
        self.ocr_frames += 1
        self._consecutive_reuses = 0
        self._last_image = image_rgb.copy()
        self._last_observations = observations
        return observations


def _nearly_identical(previous: np.ndarray, current: np.ndarray) -> bool:
    if previous.shape != current.shape or previous.dtype != np.uint8 or current.dtype != np.uint8:
        return False
    if current.ndim != 3 or current.shape[2] != 3:
        return False

    difference = np.max(
        np.abs(current.astype(np.int16) - previous.astype(np.int16)),
        axis=2,
    )
    if float(difference.mean()) > 1.5:
        return False

    changed = difference >= 12
    height, width = changed.shape
    tile_size = 32
    padded_height = ((height + tile_size - 1) // tile_size) * tile_size
    padded_width = ((width + tile_size - 1) // tile_size) * tile_size
    if padded_height != height or padded_width != width:
        changed = np.pad(
            changed,
            ((0, padded_height - height), (0, padded_width - width)),
            constant_values=False,
        )
    tile_counts = changed.reshape(
        padded_height // tile_size,
        tile_size,
        padded_width // tile_size,
        tile_size,
    ).sum(axis=(1, 3))
    return bool(np.all(tile_counts <= 2))
