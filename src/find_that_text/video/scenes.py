from __future__ import annotations

import logging
from pathlib import Path


LOGGER = logging.getLogger(__name__)


def detect_scene_changes(
    video_path: str | Path,
    *,
    start_seconds: float = 0.0,
    end_seconds: float | None = None,
) -> list[float]:
    try:
        from scenedetect import AdaptiveDetector, detect
    except ImportError:
        LOGGER.warning("PySceneDetect is unavailable; continuing without scene-change sampling.")
        return []

    try:
        scenes = detect(
            str(video_path),
            AdaptiveDetector(adaptive_threshold=3.0, min_scene_len=12),
            show_progress=False,
            start_time=start_seconds or None,
            end_time=end_seconds,
            start_in_scene=True,
            backend="pyav",
        )
    except Exception:
        LOGGER.exception("Scene detection failed; continuing with heartbeat sampling.")
        return []

    cuts = [float(scene_start.get_seconds()) for scene_start, _scene_end in scenes[1:]]
    LOGGER.info("Scene detection found %d cuts.", len(cuts))
    return cuts
