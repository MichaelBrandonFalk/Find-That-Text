from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> int:
    bundle = Path(sys.argv[1]).resolve()
    executable = bundle / "Find That Text.exe"
    if not executable.is_file():
        raise FileNotFoundError(executable)
    for model_name in ("PP-OCRv6_small_det", "PP-OCRv6_small_rec"):
        model_dir = bundle / "_internal" / "PaddleX" / "official_models" / model_name
        if not model_dir.is_dir() or not any(model_dir.iterdir()):
            raise FileNotFoundError(f"Bundled OCR model missing: {model_dir}")

    with TemporaryDirectory(prefix="find-that-text-windows-test-") as temp_dir:
        env = os.environ.copy()
        env.pop("PADDLE_PDX_CACHE_HOME", None)
        env["FIND_THAT_TEXT_APP_SUPPORT"] = temp_dir
        log_path = Path(temp_dir) / "self-test.log"
        env["FIND_THAT_TEXT_SELF_TEST_LOG"] = str(log_path)
        for argument in ("--self-test", "--self-test-gui", "--self-test-ocr"):
            print(f"Running packaged {argument}", flush=True)
            try:
                result = subprocess.run([str(executable), argument], env=env, timeout=300, check=False)
            except subprocess.TimeoutExpired as exc:
                details = log_path.read_text(encoding="utf-8") if log_path.exists() else "No test log"
                raise RuntimeError(f"Packaged {argument} timed out.\n{details}") from exc
            if result.returncode != 0:
                details = log_path.read_text(encoding="utf-8") if log_path.exists() else "No test log"
                raise RuntimeError(
                    f"Packaged {argument} failed with exit code {result.returncode}.\n{details}"
                )
        for model_name in ("PP-OCRv6_small_det", "PP-OCRv6_small_rec"):
            model_dir = Path(temp_dir) / "PaddleX" / "official_models" / model_name
            if not model_dir.is_dir() or not any(model_dir.iterdir()):
                raise FileNotFoundError(f"Bundled model was not installed: {model_dir}")
    print("Extracted Windows bundle passed import, GUI, and OCR checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
