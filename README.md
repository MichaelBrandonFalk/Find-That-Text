# Find That Text

Find visible text anywhere in a video and generate timestamped local OCR reports.

Find That Text is a local macOS utility for scanning full video frames, not just subtitle streams. It is intended for Apple Silicon Macs and uses a PaddleOCR-based OCR pipeline.

## Download

Download the Apple Silicon app from the [latest GitHub Release](https://github.com/MichaelBrandonFalk/Find-That-Text/releases/latest), or visit the [Find That Text website](https://michaelbrandonfalk.github.io/Find-That-Text/).

## What It Finds

- Phone messages
- Signs and storefront text
- Lower thirds and title cards
- Computer screens and websites
- Credits, dates, warning text, logos, and watermarks
- Text embedded in graphics or background footage

## How It Works

1. Choose or drop in a MOV, MP4, or M4V video.
2. Select Default, Advanced, or a custom frame interval.
3. Adjust Text Strictness to include uncertain results or retain only clear text.
4. Scan locally on your Mac.
5. Review the CSV, HTML report, evidence screenshots, and raw OCR JSON.

Default mode checks every 23rd frame. Advanced mode checks every frame. Custom mode checks every frame interval you specify. The full video is scanned unless you enter a start and/or end timestamp such as `00:00:00` to `00:30:30`.

## Reports

Each scan writes a folder containing:

- `report.html` - searchable local HTML report
- `report.csv` - QC-friendly event summary
- `raw_detections.json` - every raw OCR detection
- `screenshots/` - clean and optional annotated evidence frames

## Privacy

All normal scanning is local. Videos, screenshots, OCR results, filenames, and reports are not uploaded by Find That Text. See [PRIVACY.md](PRIVACY.md).

## System Requirements

- Apple Silicon Mac
- macOS 14 or newer is the current packaging target because several current arm64 wheels target macOS 14+
- Python 3.13 for development builds

## Build From Source

```bash
cd find-that-text
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pytest
python -m find_that_text.cli --help
```

To run the GUI from source:

```bash
python -m find_that_text.app
```

PaddleOCR/PaddleX model cache files are stored under `~/Library/Application Support/Find That Text/PaddleX` by default. For validation or portable test runs, set `FIND_THAT_TEXT_APP_SUPPORT` or `PADDLE_PDX_CACHE_HOME` before launching.

Release builds can include `.paddlex-cache/official_models` as bundled resources. On first launch, the app copies those bundled models into the writable PaddleX cache before initializing OCR so ordinary scans do not require internet access.

To scan from the CLI:

```bash
find-that-text scan "/path/to/movie.mov" --mode default
find-that-text scan "/path/to/movie.mov" --mode advanced --start 00:00:00 --end 00:30:30
find-that-text scan "/path/to/movie.mov" --mode custom --custom-frame-step 7 --min-confidence 0.75
```

## Packaging

The packaging scripts target an onedir PyInstaller macOS `.app` bundle, then wrap it in a DMG. Onefile packaging is intentionally avoided for the ML-heavy runtime.

```bash
scripts/build_macos.sh
scripts/package_dmg.sh
```

Signing and notarization are supported when Apple Developer credentials are provided through environment variables in the release workflow. Unsigned builds can still be produced for local testing.

## Current Validation Status

See [docs/technical-validation.md](docs/technical-validation.md). The repository includes implementation, tests for tracking/reporting logic, CI/release/Pages workflows, and packaging scripts. OCR/video/package proof tests must be run in a fresh Apple Silicon environment before publishing `v1.0.0`.

## License

Find That Text is released under the MIT License. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for dependency license notes.
