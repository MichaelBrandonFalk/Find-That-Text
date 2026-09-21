from __future__ import annotations


def format_timestamp(seconds: float | int | None) -> str:
    if seconds is None:
        seconds = 0
    total_ms = max(0, int(round(float(seconds) * 1000)))
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    sec = total_seconds % 60
    total_minutes = total_seconds // 60
    minute = total_minutes % 60
    hour = total_minutes // 60
    return f"{hour:02d}:{minute:02d}:{sec:02d}.{ms:03d}"


def parse_timestamp(value: str) -> float:
    raw = value.strip()
    if not raw:
        raise ValueError("Timestamp cannot be empty.")
    if ":" not in raw:
        seconds = float(raw)
        if seconds < 0:
            raise ValueError("Timestamp cannot be negative.")
        return seconds

    time_part, dot, fractional_part = raw.partition(".")
    parts = [int(part) for part in time_part.split(":")]
    if len(parts) == 2:
        hour = 0
        minute, second = parts
    elif len(parts) == 3:
        hour, minute, second = parts
    else:
        raise ValueError("Use SS, MM:SS, or HH:MM:SS timestamp format.")
    if minute >= 60 or second >= 60 or min(parts) < 0:
        raise ValueError("Timestamp minutes and seconds must be between 0 and 59.")

    fraction = 0.0
    if dot:
        fraction = float(f"0.{fractional_part}")
    return hour * 3600 + minute * 60 + second + fraction
