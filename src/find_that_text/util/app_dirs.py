from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path


APP_NAME = "Find That Text"


def app_support_dir() -> Path:
    override = os.environ.get("FIND_THAT_TEXT_APP_SUPPORT")
    if override:
        return Path(override).expanduser()
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / ".find-that-text"


def configure_paddle_cache() -> Path:
    os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
    cache_dir = app_support_dir() / "PaddleX"
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(cache_dir))
    resolved_cache = Path(os.environ["PADDLE_PDX_CACHE_HOME"]).expanduser()
    install_bundled_paddlex_models(resolved_cache)
    return resolved_cache


def install_bundled_paddlex_models(cache_dir: Path) -> None:
    bundled = bundled_paddlex_dir()
    if not bundled.exists():
        return
    source = bundled / "official_models"
    if not source.exists():
        return
    destination = cache_dir / "official_models"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return
    shutil.copytree(source, destination)


def bundled_paddlex_dir() -> Path:
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        return executable.parents[1] / "Resources" / "PaddleX"
    return Path(__file__).resolve().parents[3] / ".paddlex-cache"
