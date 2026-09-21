from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def safe_stem(path: str | Path) -> str:
    stem = Path(path).stem.strip() or "video"
    stem = re.sub(r"[^\w .()'&+-]+", "_", stem, flags=re.UNICODE)
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem[:120] or "video"


def default_reports_root() -> Path:
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        return desktop / "Find That Text Reports"
    return Path.home() / "Find That Text Reports"


def create_output_dir(video_path: str | Path, root: str | Path | None = None) -> Path:
    root_path = Path(root).expanduser() if root else default_reports_root()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = root_path / f"{safe_stem(video_path)}_FindThatText_{stamp}"
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "screenshots").mkdir(parents=True, exist_ok=True)
    return output_dir
