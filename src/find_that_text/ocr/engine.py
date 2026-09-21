from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from find_that_text.tracking.geometry import box_to_polygon, polygon_to_box
from find_that_text.util.app_dirs import bundled_paddlex_dir, configure_paddle_cache


@dataclass(slots=True)
class OCRTextObservation:
    text: str
    confidence: float
    polygon: list[list[float]]
    box: tuple[float, float, float, float]


class OCREngine(Protocol):
    name: str

    def recognize(self, image_rgb: np.ndarray) -> list[OCRTextObservation]:
        ...


class PaddleOCREngine:
    name = "PaddleOCR"

    def __init__(
        self,
        *,
        engine: str | None = None,
        lang: str | None = None,
        text_detection_model_name: str | None = None,
        text_recognition_model_name: str | None = None,
    ) -> None:
        configure_paddle_cache()
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:  # pragma: no cover - exercised in dependency spike
            raise RuntimeError("PaddleOCR is not installed. Install the pinned runtime.") from exc

        kwargs: dict[str, Any] = {
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
            "device": "cpu",
        }
        bundled_config = bundled_ocr_pipeline_config()
        if bundled_config is not None:
            kwargs["paddlex_config"] = str(bundled_config)
        if engine:
            kwargs["engine"] = engine
        if lang:
            kwargs["lang"] = lang
        if text_detection_model_name:
            kwargs["text_detection_model_name"] = text_detection_model_name
        if text_recognition_model_name:
            kwargs["text_recognition_model_name"] = text_recognition_model_name

        self._ocr = PaddleOCR(**kwargs)
        self.backend = engine or "paddle"
        self.model_description = (
            f"det={text_detection_model_name or 'default'}, "
            f"rec={text_recognition_model_name or 'default'}, engine={self.backend}"
        )

    def recognize(self, image_rgb: np.ndarray) -> list[OCRTextObservation]:
        result = self._ocr.predict(image_rgb)
        return observations_from_paddle_result(result)


def bundled_ocr_pipeline_config() -> Path | None:
    config = bundled_paddlex_dir() / "configs" / "pipelines" / "OCR.yaml"
    if config.exists():
        return config
    return None


class EmptyOCREngine:
    name = "Empty OCR"
    model_description = "test-empty"

    def recognize(self, image_rgb: np.ndarray) -> list[OCRTextObservation]:
        return []


def observations_from_paddle_result(result: Any) -> list[OCRTextObservation]:
    observations: list[OCRTextObservation] = []
    for item in _iter_result_items(result):
        observations.extend(_observations_from_item(item))
    return observations


def _iter_result_items(result: Any) -> list[Any]:
    if result is None:
        return []
    if isinstance(result, list):
        return result
    return [result]


def _mapping_from_result_item(item: Any) -> dict[str, Any] | None:
    if isinstance(item, dict):
        return item.get("res", item)
    for attr in ("json", "res", "data"):
        value = getattr(item, attr, None)
        if isinstance(value, dict):
            return value.get("res", value)
    to_dict = getattr(item, "to_dict", None)
    if callable(to_dict):
        value = to_dict()
        if isinstance(value, dict):
            return value.get("res", value)
    return None


def _observations_from_item(item: Any) -> list[OCRTextObservation]:
    if _looks_like_legacy_line(item):
        return [_legacy_line_to_observation(item)]

    mapping = _mapping_from_result_item(item)
    if mapping is None:
        if isinstance(item, list):
            return [_legacy_line_to_observation(line) for line in item if _looks_like_legacy_line(line)]
        return []

    texts = _first_present(mapping, "rec_texts", "texts")
    scores = _first_present(mapping, "rec_scores", "scores")
    polygons = _first_present(mapping, "rec_polys", "dt_polys")
    boxes = _first_present(mapping, "rec_boxes", "boxes")

    output: list[OCRTextObservation] = []
    for index, text in enumerate(texts):
        if not str(text).strip():
            continue
        score = float(scores[index]) if index < len(scores) else 0.0
        polygon = _coerce_polygon(polygons[index]) if index < len(polygons) else []
        if not polygon and index < len(boxes):
            box = _coerce_box(boxes[index])
            polygon = box_to_polygon(box)
        box = polygon_to_box(polygon)
        output.append(OCRTextObservation(str(text), score, polygon, box))
    return output


def _first_present(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return []


def _looks_like_legacy_line(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) >= 2
        and isinstance(value[1], (list, tuple))
        and len(value[1]) >= 2
    )


def _legacy_line_to_observation(line: Any) -> OCRTextObservation:
    polygon = _coerce_polygon(line[0])
    text = str(line[1][0])
    score = float(line[1][1])
    return OCRTextObservation(text, score, polygon, polygon_to_box(polygon))


def _coerce_polygon(value: Any) -> list[list[float]]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not value:
        return []
    return [[float(point[0]), float(point[1])] for point in value]


def _coerce_box(value: Any) -> tuple[float, float, float, float]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if len(value) == 4:
        x0, y0, x1, y1 = [float(v) for v in value]
        if x1 >= x0 and y1 >= y0:
            return (x0, y0, x1 - x0, y1 - y0)
        return (x0, y0, x1, y1)
    return polygon_to_box(_coerce_polygon(value))
