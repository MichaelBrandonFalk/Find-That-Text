from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys


@lru_cache(maxsize=1)
def get_version() -> str:
    candidates: list[Path] = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "VERSION")
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        candidates.extend(
            [
                executable.parents[1] / "Resources" / "VERSION",
                executable.parents[1] / "Frameworks" / "VERSION",
            ]
        )
    candidates.append(Path(__file__).resolve().parents[2] / "VERSION")
    for version_file in candidates:
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip()
    return "0.0.0"


__version__ = get_version()
