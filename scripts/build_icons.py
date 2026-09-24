from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "packaging" / "logo-source.png"


def save_square(image: Image.Image, size: int, path: Path) -> None:
    image.resize((size, size), Image.Resampling.LANCZOS).save(path, format="PNG")


def main() -> None:
    with Image.open(SOURCE) as source:
        logo = source.convert("RGBA")
    if logo.width != logo.height:
        raise ValueError("The supplied logo must be square for app and browser icons.")

    with tempfile.TemporaryDirectory(prefix="find-that-text-iconset-") as temp_dir:
        iconset = Path(temp_dir) / "FindThatText.iconset"
        iconset.mkdir()
        for size in (16, 32, 128, 256, 512):
            save_square(logo, size, iconset / f"icon_{size}x{size}.png")
            save_square(logo, size * 2, iconset / f"icon_{size}x{size}@2x.png")
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(ROOT / "packaging" / "FindThatText.icns")],
            check=True,
        )

    save_square(logo, 512, ROOT / "src" / "find_that_text" / "resources" / "app-icon.png")
    web_assets = ROOT / "site" / "assets"
    for size, name in (
        (32, "favicon-32.png"),
        (180, "apple-touch-icon.png"),
        (192, "icon-192.png"),
        (512, "icon-512.png"),
    ):
        save_square(logo, size, web_assets / name)


if __name__ == "__main__":
    main()
