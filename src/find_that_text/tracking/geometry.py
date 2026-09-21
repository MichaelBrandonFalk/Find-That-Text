from __future__ import annotations

from collections.abc import Sequence
from math import hypot

Point = tuple[float, float]
Box = tuple[float, float, float, float]


def polygon_to_box(polygon: Sequence[Sequence[float]] | None) -> Box:
    if not polygon:
        return (0.0, 0.0, 0.0, 0.0)
    xs = [float(point[0]) for point in polygon]
    ys = [float(point[1]) for point in polygon]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return (min_x, min_y, max_x - min_x, max_y - min_y)


def box_to_polygon(box: Sequence[float]) -> list[list[float]]:
    x, y, width, height = [float(v) for v in box]
    return [[x, y], [x + width, y], [x + width, y + height], [x, y + height]]


def box_area(box: Sequence[float]) -> float:
    return max(0.0, float(box[2])) * max(0.0, float(box[3]))


def box_iou(a: Sequence[float], b: Sequence[float]) -> float:
    ax, ay, aw, ah = [float(v) for v in a]
    bx, by, bw, bh = [float(v) for v in b]
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh
    inter_w = max(0.0, min(ax2, bx2) - max(ax, bx))
    inter_h = max(0.0, min(ay2, by2) - max(ay, by))
    inter = inter_w * inter_h
    union = box_area(a) + box_area(b) - inter
    return inter / union if union else 0.0


def center_distance_ratio(a: Sequence[float], b: Sequence[float], width: int, height: int) -> float:
    ax, ay, aw, ah = [float(v) for v in a]
    bx, by, bw, bh = [float(v) for v in b]
    diagonal = hypot(max(width, 1), max(height, 1))
    return hypot((ax + aw / 2) - (bx + bw / 2), (ay + ah / 2) - (by + bh / 2)) / diagonal


def union_box(boxes: Sequence[Sequence[float]]) -> Box:
    if not boxes:
        return (0.0, 0.0, 0.0, 0.0)
    min_x = min(float(box[0]) for box in boxes)
    min_y = min(float(box[1]) for box in boxes)
    max_x = max(float(box[0]) + float(box[2]) for box in boxes)
    max_y = max(float(box[1]) + float(box[3]) for box in boxes)
    return (min_x, min_y, max_x - min_x, max_y - min_y)


def classify_position(box: Sequence[float], frame_width: int, frame_height: int) -> str:
    x, y, width, height = [float(v) for v in box]
    if frame_width <= 0 or frame_height <= 0:
        return "Unknown"
    if width / frame_width > 0.65 or height / frame_height > 0.45:
        return "Multiple / Large Area"
    cx = (x + width / 2) / frame_width
    cy = (y + height / 2) / frame_height
    horizontal = "Left" if cx < 1 / 3 else "Right" if cx > 2 / 3 else "Center"
    vertical = "Upper" if cy < 1 / 3 else "Lower" if cy > 2 / 3 else "Center"
    if horizontal == "Center" and vertical == "Center":
        return "Center"
    return f"{vertical} {horizontal}"
