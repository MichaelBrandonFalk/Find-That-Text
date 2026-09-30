#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

python3 -m pip install -r requirements-linux-x64.txt
python3 -m pip install -e . --no-deps
python3 -m pytest
python3 scripts/release_check.py

export PADDLE_PDX_CACHE_HOME="$root/.paddlex-cache"
export PADDLE_PDX_MODEL_SOURCE=bos
python3 -c 'from find_that_text.ocr.engine import PaddleOCREngine; PaddleOCREngine()'

python3 -m PyInstaller --clean --noconfirm packaging/FindThatTextLinux.spec

version="$(tr -d '\r\n' < VERSION)"
archive="dist/Find-That-Text-v${version}-Linux-x64.tar.gz"
tar -C dist -czf "$archive" "Find That Text"
printf 'Built %s\n' "$archive"
