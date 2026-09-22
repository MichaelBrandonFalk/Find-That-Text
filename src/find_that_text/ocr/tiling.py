from __future__ import annotations

from collections.abc import Iterable

import numpy as np

from find_that_text.ocr.engine import OCREngine, OCRTextObservation
from find_that_text.ocr.normalize import normalize_text
from find_that_text.tracking.geometry import box_iou


def recognize_with_optional_tiling(
    engine: OCREngine,
    image_rgb: np.ndarray,
    *,
    enable_tiling: bool,
) -> list[OCRTextObservation]:
    observations = list(engine.recognize(image_rgb))
    if not enable_tiling:
        return observations

    height, width = image_rgb.shape[:2]
    tile_observations: list[OCRTextObservation] = []
    for tile, offset_x, offset_y in _iter_tiles(image_rgb, rows=2, cols=2, overlap=0.15):
        for observation in engine.recognize(tile):
            tile_observations.append(_translate_observation(observation, offset_x, offset_y))
    return _dedupe_observations([*observations, *tile_observations], width=width, height=height)


def _iter_tiles(
    image_rgb: np.ndarray,
    *,
    rows: int,
    cols: int,
    overlap: float,
) -> Iterable[tuple[np.ndarray, int, int]]:
    height, width = image_rgb.shape[:2]
    tile_width = int(width / cols)
    tile_height = int(height / rows)
    pad_x = int(tile_width * overlap)
    pad_y = int(tile_height * overlap)
    for row in range(rows):
        for col in range(cols):
            x0 = max(0, col * tile_width - pad_x)
            y0 = max(0, row * tile_height - pad_y)
            x1 = min(width, (col + 1) * tile_width + pad_x)
            y1 = min(height, (row + 1) * tile_height + pad_y)
            yield image_rgb[y0:y1, x0:x1], x0, y0


def _translate_observation(
    observation: OCRTextObservation,
    offset_x: int,
    offset_y: int,
) -> OCRTextObservation:
    polygon = [[point[0] + offset_x, point[1] + offset_y] for point in observation.polygon]
    box = (
        observation.box[0] + offset_x,
        observation.box[1] + offset_y,
        observation.box[2],
        observation.box[3],
    )
    return OCRTextObservation(
        observation.text,
        observation.confidence,
        polygon,
        box,
        observation.detector_confidence,
    )


def _dedupe_observations(
    observations: list[OCRTextObservation],
    *,
    width: int,
    height: int,
) -> list[OCRTextObservation]:
    del width, height
    kept: list[OCRTextObservation] = []
    for observation in sorted(observations, key=lambda item: item.confidence, reverse=True):
        normalized = normalize_text(observation.text)
        duplicate = any(
            normalize_text(existing.text) == normalized and box_iou(existing.box, observation.box) > 0.45
            for existing in kept
        )
        if not duplicate:
            kept.append(observation)
    return kept
