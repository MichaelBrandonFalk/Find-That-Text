from __future__ import annotations

import logging
import platform
from pathlib import Path

from find_that_text.version import __version__


def configure_logging(output_dir: Path | None = None) -> Path | None:
    log_path = output_dir / "find-that-text.log" if output_dir else None
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_path:
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    logging.info(
        "Find That Text %s on macOS=%s architecture=%s",
        __version__,
        platform.mac_ver()[0],
        platform.machine(),
    )
    return log_path
