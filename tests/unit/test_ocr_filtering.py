from __future__ import annotations

import pytest

from find_that_text.ocr.engine import OCRTextObservation
from find_that_text.scanner import filter_ocr_observations, validate_min_ocr_confidence


def observation(text: str, confidence: float) -> OCRTextObservation:
    return OCRTextObservation(text, confidence, [], (0.0, 0.0, 0.0, 0.0))


def test_confidence_filter_keeps_results_at_or_above_threshold() -> None:
    observations = [
        observation("possible decoration", 0.49),
        observation("borderline text", 0.5),
        observation("clear text", 0.92),
        observation("   ", 0.99),
    ]

    kept = filter_ocr_observations(observations, 0.5)

    assert [item.text for item in kept] == ["borderline text", "clear text"]


@pytest.mark.parametrize("value", [-0.01, 1.01, float("nan")])
def test_confidence_threshold_rejects_out_of_range_values(value: float) -> None:
    with pytest.raises(ValueError, match="between 0% and 100%"):
        validate_min_ocr_confidence(value)
