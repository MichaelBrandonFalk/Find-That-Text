from __future__ import annotations

from pathlib import Path

from PIL import Image


root = Path(__file__).resolve().parents[1]
with Image.open(root / "packaging" / "logo-source.png") as source:
    source.convert("RGBA").save(
        root / "packaging" / "FindThatText.ico",
        format="ICO",
        sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)],
    )
