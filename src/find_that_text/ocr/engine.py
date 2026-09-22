from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from find_that_text.tracking.geometry import box_to_polygon, polygon_to_box
from find_that_text.util.app_dirs import configure_paddle_cache


@dataclass(slots=True)
class OCRTextObservation:
    text: str
    confidence: float
    polygon: list[list[float]]
    box: tuple[float, float, float, float]
    detector_confidence: float | None = None


class OCREngine(Protocol):
    name: str

    def recognize(self, image_rgb: np.ndarray) -> list[OCRTextObservation]:
        ...


class PaddleOCREngine:
    name = "PaddleOCR"

    DEFAULT_DETECTION_MODEL = "PP-OCRv6_small_det"
    DEFAULT_RECOGNITION_MODEL = "PP-OCRv6_small_rec"

    def __init__(
        self,
        *,
        engine: str | None = None,
        lang: str | None = None,
        text_detection_model_name: str | None = None,
        text_recognition_model_name: str | None = None,
        text_det_thresh: float = 0.25,
        text_det_box_thresh: float = 0.45,
        text_rec_score_thresh: float = 0.0,
    ) -> None:
        configure_paddle_cache()
        try:
            from paddleocr import TextDetection, TextRecognition
        except ImportError as exc:  # pragma: no cover - exercised in dependency spike
            raise RuntimeError("PaddleOCR is not installed. Install the pinned runtime.") from exc

        shared_kwargs: dict[str, Any] = {"device": "cpu"}
        if engine:
            shared_kwargs["engine"] = engine
        del lang
        detection_model = text_detection_model_name or self.DEFAULT_DETECTION_MODEL
        recognition_model = text_recognition_model_name or self.DEFAULT_RECOGNITION_MODEL
        self._detector = TextDetection(
            model_name=detection_model,
            thresh=text_det_thresh,
            box_thresh=text_det_box_thresh,
            **shared_kwargs,
        )
        self._recognizer = TextRecognition(model_name=recognition_model, **shared_kwargs)
        self.backend = engine or "paddle"
        self.text_det_thresh = text_det_thresh
        self.text_det_box_thresh = text_det_box_thresh
        self.text_rec_score_thresh = text_rec_score_thresh
        self.model_description = (
            f"det={detection_model}, rec={recognition_model}, engine={self.backend}"
        )

    def recognize(self, image_rgb: np.ndarray) -> list[OCRTextObservation]:
        detector_result = self._detector.predict(image_rgb, batch_size=1)
        polygons: list[list[list[float]]] = []
        detector_scores: list[float] = []
        for item in detector_result:
            mapping = _mapping_from_result_item(item) or {}
            item_polygons = _first_present(mapping, "dt_polys", "polys")
            item_scores = _first_present(mapping, "dt_scores", "scores")
            for index, raw_polygon in enumerate(item_polygons):
                polygon = _coerce_polygon(raw_polygon)
                if not polygon:
                    continue
                polygons.append(polygon)
                detector_scores.append(float(item_scores[index]) if index < len(item_scores) else 0.0)

        crops = [_crop_polygon(image_rgb, polygon) for polygon in polygons]
        valid = [index for index, crop in enumerate(crops) if crop.size]
        if not valid:
            return []
        recognition_result = self._recognizer.predict(
            [crops[index] for index in valid],
            batch_size=min(16, len(valid)),
        )

        observations: list[OCRTextObservation] = []
        for result_index, item in enumerate(recognition_result):
            if result_index >= len(valid):
                break
            mapping = _mapping_from_result_item(item) or {}
            text = str(mapping.get("rec_text", mapping.get("text", ""))).strip()
            score = float(mapping.get("rec_score", mapping.get("score", 0.0)))
            if not text or score < self.text_rec_score_thresh:
                continue
            polygon_index = valid[result_index]
            polygon = polygons[polygon_index]
            observations.append(
                OCRTextObservation(
                    text,
                    score,
                    polygon,
                    polygon_to_box(polygon),
                    detector_scores[polygon_index],
                )
            )
        return observations


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
    detector_scores = _first_present(mapping, "dt_scores", "det_scores")

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
        detector_score = float(detector_scores[index]) if index < len(detector_scores) else None
        output.append(OCRTextObservation(str(text), score, polygon, box, detector_score))
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


def _crop_polygon(image_rgb: np.ndarray, polygon: list[list[float]]) -> np.ndarray:
    points = np.asarray(polygon, dtype=np.float32)
    if points.shape != (4, 2):
        x, y, width, height = polygon_to_box(polygon)
        return image_rgb[
            max(0, int(y)) : min(image_rgb.shape[0], int(y + height)),
            max(0, int(x)) : min(image_rgb.shape[1], int(x + width)),
        ]

    try:
        import cv2
    except ImportError:  # pragma: no cover - OpenCV ships with PaddleOCR
        x, y, width, height = polygon_to_box(polygon)
        return image_rgb[
            max(0, int(y)) : min(image_rgb.shape[0], int(y + height)),
            max(0, int(x)) : min(image_rgb.shape[1], int(x + width)),
        ]

    width = max(
        int(np.linalg.norm(points[0] - points[1])),
        int(np.linalg.norm(points[2] - points[3])),
        1,
    )
    height = max(
        int(np.linalg.norm(points[0] - points[3])),
        int(np.linalg.norm(points[1] - points[2])),
        1,
    )
    destination = np.asarray(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(points, destination)
    crop = cv2.warpPerspective(image_rgb, transform, (width, height), borderMode=cv2.BORDER_REPLICATE)
    if height > width * 1.5:
        crop = np.rot90(crop)
    return crop
