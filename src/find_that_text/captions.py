from __future__ import annotations

import bisect
import re
from dataclasses import dataclass
from pathlib import Path


_TIMING_LINE = re.compile(
    r"(?P<start>(?:\d{1,3}:)?\d{1,2}:\d{2}[.,]\d{3})\s*-->\s*"
    r"(?P<end>(?:\d{1,3}:)?\d{1,2}:\d{2}[.,]\d{3})"
)


@dataclass(frozen=True, slots=True)
class CaptionCue:
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True, slots=True)
class CaptionTimeline:
    path: Path
    cues: tuple[CaptionCue, ...]
    _starts: tuple[float, ...]

    @classmethod
    def from_file(cls, path: str | Path) -> CaptionTimeline:
        caption_path = Path(path)
        if caption_path.suffix.lower() not in {".srt", ".vtt"}:
            raise ValueError("Dialogue captions must be an SRT or VTT file.")
        text = caption_path.read_text(encoding="utf-8-sig", errors="replace")
        cues: list[CaptionCue] = []
        for line in text.splitlines():
            match = _TIMING_LINE.search(line)
            if not match:
                continue
            start = _parse_caption_timestamp(match.group("start"))
            end = _parse_caption_timestamp(match.group("end"))
            if end > start:
                cues.append(CaptionCue(start, end))
        if not cues:
            raise ValueError(f"No timed caption cues were found in {caption_path.name}.")
        merged = _merge_cues(cues)
        return cls(caption_path, tuple(merged), tuple(cue.start_seconds for cue in merged))

    def is_dialogue_active(self, timestamp_seconds: float, *, padding_seconds: float = 0.15) -> bool:
        if not self.cues:
            return False
        index = bisect.bisect_right(self._starts, timestamp_seconds + padding_seconds) - 1
        if index < 0:
            return False
        cue = self.cues[index]
        return cue.start_seconds - padding_seconds <= timestamp_seconds <= cue.end_seconds + padding_seconds

    def dialogue_free_ratio(self, timestamps: list[float]) -> float:
        if not timestamps:
            return 0.0
        quiet = sum(not self.is_dialogue_active(timestamp) for timestamp in timestamps)
        return quiet / len(timestamps)

    def quiet_gap_starts(
        self,
        *,
        start_seconds: float = 0.0,
        end_seconds: float | None = None,
        minimum_gap_seconds: float = 0.4,
    ) -> list[float]:
        boundaries: list[float] = []
        for index, cue in enumerate(self.cues):
            next_start = self.cues[index + 1].start_seconds if index + 1 < len(self.cues) else end_seconds
            if next_start is None or next_start - cue.end_seconds >= minimum_gap_seconds:
                if cue.end_seconds >= start_seconds and (end_seconds is None or cue.end_seconds <= end_seconds):
                    boundaries.append(cue.end_seconds + 0.05)
        return boundaries


def find_sidecar_caption(video_path: str | Path) -> Path | None:
    video = Path(video_path)
    exact = [video.with_suffix(".srt"), video.with_suffix(".vtt")]
    for candidate in exact:
        if candidate.is_file():
            return candidate

    stem = video.stem.casefold()
    language_tokens = ("en", "eng", "english", "es", "spa", "spanish")
    candidates = [
        path
        for path in video.parent.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".srt", ".vtt"}
        and path.stem.casefold().startswith(stem)
        and (
            len(path.stem) == len(video.stem)
            or path.stem[len(video.stem)] in " ._-(["
        )
    ]

    def rank(path: Path) -> tuple[int, str]:
        suffix = path.stem.casefold()[len(stem) :].strip(" ._-()[]")
        language_match = any(token in re.split(r"[ ._\-()\[\]]+", suffix) for token in language_tokens)
        return (0 if language_match else 1, path.name.casefold())

    return min(candidates, key=rank) if candidates else None


def _parse_caption_timestamp(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise ValueError(f"Invalid caption timestamp: {value}")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _merge_cues(cues: list[CaptionCue]) -> list[CaptionCue]:
    merged: list[CaptionCue] = []
    for cue in sorted(cues, key=lambda item: (item.start_seconds, item.end_seconds)):
        if merged and cue.start_seconds <= merged[-1].end_seconds + 0.05:
            previous = merged[-1]
            merged[-1] = CaptionCue(previous.start_seconds, max(previous.end_seconds, cue.end_seconds))
        else:
            merged.append(cue)
    return merged
