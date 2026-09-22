# Find That Text

Find likely forced-text moments in a movie without rewatching the entire program.

Find That Text is a free, open-source macOS utility for subtitle and localization teams. It scans visible text in video frames, groups repeated detections into screen-text moments, and produces a ranked local review report. It is designed for Apple Silicon Macs and keeps the video, captions, screenshots, and OCR results on the computer.

## Download

Download the Apple Silicon app from the [latest GitHub Release](https://github.com/MichaelBrandonFalk/Find-That-Text/releases/latest), or visit the [Find That Text website](https://michaelbrandonfalk.github.io/Find-That-Text/).

## What It Finds

- Opening titles and location/date cards
- Phone messages and computer screens
- Plot-relevant signs, letters, and warnings
- Lower thirds and other embedded graphics
- Credits, logos, watermarks, and uncertain text for secondary review

The app does not decide what is essential to the plot. It creates a short, ranked set of moments for a human reviewer.

## Recommended Scan

1. Choose or drop in a MOV, MP4, or M4V video.
2. Optionally choose English or Spanish dialogue captions in SRT or VTT format. A matching sidecar is selected automatically when available.
3. Leave **Scan dialogue gaps more closely** enabled to scan silent sections more densely.
4. Scan the full video or enter an optional start/end range.
5. Review **Likely Forced Text** first, then **Needs Review**. Background graphics and credits remain available in a collapsed section.

Captions are optional. Without captions, Find That Text uses a uniform adaptive scan and scene changes. This supports workflows both before and after dialogue captions are created.

## How Scanning Works

Recommended mode uses several signals together:

- A one-second heartbeat when no dialogue captions are available
- Half-second sampling in dialogue-free gaps and two-second sampling during dialogue when optimization is enabled
- Priority samples at quiet-gap boundaries and scene changes
- PP-OCRv6 small detection and recognition models on frames capped at 1280 pixels
- Detector confidence, OCR confidence, temporal confirmation, text shape, screen size and position, dialogue gaps, repeated graphics, and credit-density scoring

Nothing is removed solely because it receives a low relevance score. Every grouped event is included in one of three report sections, and the raw JSON preserves the underlying detections.

Diagnostic every-frame mode and a custom frame interval remain available under Advanced Settings. Every-frame mode is intended for short ranges because a feature-length scan can take much longer.

## Reports

Each scan writes a folder containing:

- `report.html` - ranked and searchable forced-text candidate report
- `report.csv` - QC-friendly event summary with scores and reasons
- `raw_detections.json` - every OCR detection and scan setting
- `screenshots/` - clean and optional annotated evidence frames

## Performance Target

The recommended pipeline is designed to scan a two-hour feature in two hours or less on supported Apple Silicon hardware. Actual time depends on the Mac, source codec, dialogue density, scene count, and detected text volume. Full-feature benchmarking remains part of release validation; the app does not present a guaranteed completion time.

## Privacy

All normal scanning is local. Videos, caption files, screenshots, OCR results, filenames, and reports are not uploaded by Find That Text. See [PRIVACY.md](PRIVACY.md).

## System Requirements

- Apple Silicon Mac
- macOS 14 or newer
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

To run the GUI:

```bash
python -m find_that_text.app
```

To scan from the CLI:

```bash
find-that-text scan "/path/to/movie.mov" --captions "/path/to/movie.en.srt"
find-that-text scan "/path/to/movie.mov" --captions "/path/to/movie.es.vtt" --start 00:00:00 --end 00:30:30
find-that-text scan "/path/to/movie.mov" --no-dialogue-optimization
find-that-text scan "/path/to/movie.mov" --mode custom --custom-frame-step 7 --review-breadth 0.35
```

Release builds bundle the PP-OCRv6 small models. On first launch, the app copies those models into `~/Library/Application Support/Find That Text/PaddleX`; normal scans do not need internet access.

## Packaging

```bash
scripts/build_macos.sh
scripts/package_dmg.sh
```

The build creates a PyInstaller `.app` bundle and an Apple Silicon DMG. Signing and notarization are used when Apple Developer credentials are provided. Unsigned builds may require macOS **Open** or **Open Anyway**.

## License

Find That Text is released under the MIT License. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for dependency license notes.
