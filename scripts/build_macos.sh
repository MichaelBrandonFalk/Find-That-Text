#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest
python scripts/release_check.py
python -m PyInstaller --clean --noconfirm packaging/FindThatText.spec

echo "Built dist/Find That Text.app"
