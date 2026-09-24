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
2. Add an English or Spanish dialogue SRT/VTT file. A matching sidecar is selected automatically when available.
3. Leave **Scan only where dialogue captions are absent** and **Fastest - every 23 frames** selected.
4. Scan the full video or enter an optional start/end range.
5. Review **Likely Forced Text** first, then **Needs Review**. Background graphics and credits remain available in a collapsed section.

With captions, the default **Minimum dialogue-free break** is 1.0 second. Shorter breaks are skipped before OCR; the adjustable slider runs from 0 to 5 seconds in 0.1-second steps. The threshold measures the caption-free break before the 0.15-second speech margins. The same threshold applies to Super Speed Run's exported timecodes. With no captions, this setting has no effect.

The two speed choices are independent. Turn off gap-only scanning to include text that appears during dialogue, or choose a closer frame interval under Advanced Settings. With no captions, the app scans the whole video every 23 frames. This supports workflows both before and after dialogue captions are created.

To get dialogue-free timecodes without looking for screen text, select **Super Speed Run - dialogue gaps only** under Run. It requires an English or Spanish SRT/VTT file, reads video timing metadata, and writes `dialogue_gaps.html` and `dialogue_gaps.csv`. It does not decode video frames or run OCR. Use the regular **Screen-text scan** to find forced-text candidates.

## How Scanning Works

Fastest mode is the default:

- Check every 23rd source frame and send only those frames to OCR
- Add one midpoint check in each eligible dialogue gap shorter than that sampling interval, so a one-second break is not missed by cadence alone
- With dialogue captions, first build a dialogue-gap timeline, then OCR only sampled frames in those gaps (including a 0.15-second margin around speech)
- Recognized music, lyrics marked with musical notes, and sound-effect-only cues count as scan time; cues mixing speech and sounds count as dialogue
- With no captions, scan sampled frames across the full video
- Reuse OCR results on near-identical sampled frames, with a fresh OCR pass after at most two reuses
- Skip the full-video scene-change prepass
- PP-OCRv6 small detection and recognition models on frames capped at 1280 pixels
- Detector confidence, OCR confidence, temporal confirmation, text shape, screen size and position, dialogue gaps, repeated graphics, and credit-density scoring

Nothing is removed solely because it receives a low relevance score. Every grouped event is included in one of three report sections, and the raw JSON preserves the underlying detections.

Readable English or Spanish words now carry more weight in ranking, even if some OCR on the same screen is garbled. A high detector confidence or many letters alone cannot put text with no common recognizable words in **Likely Forced Text**. Proper names, unusual typography, and less-common languages may still appear in **Needs Review**. A busy screen is no longer assumed to be rolling credits just because many text detections appear nearby.

Gap-only scanning can miss plot text shown while people speak, and sampling can miss very brief text. Caption cue classification is heuristic: uncommon sound-effect wording or unmarked lyrics may still be treated as dialogue. For broader coverage, turn off the gap-only checkbox, use Adaptive or a smaller custom frame interval, and optionally enable scene-change detection. Every-frame mode is intended for short ranges because a feature-length scan can take much longer. These controls can be changed separately. If you clear an automatically selected caption file, it will not be silently reselected for that scan.

OCR reuse is intentionally conservative: meaningful local pixel changes trigger a fresh OCR pass, and every third near-identical sample is refreshed. It is disabled in every-frame mode and when UHD tiling is enabled. The report shows analyzed and reused frame counts. Moving scenes may not benefit, so this is a speed aid rather than a guaranteed time reduction.

## Reports

Each scan writes a folder containing:

- `report.html` - ranked and searchable forced-text candidate report
- `shareable_report.html` - single-file report with embedded evidence frames for coworkers
- `report.xlsx` - filterable spreadsheet with clickable links to evidence screenshots
- `report.csv` - QC-friendly event summary with scores and reasons
- `raw_detections.json` - every OCR detection and scan setting
- `screenshots/` - clean and optional annotated evidence frames
- `dialogue_gaps.html` and `dialogue_gaps.csv` - dialogue-free ranges when captions are supplied

By default, report folders are created in `~/Downloads/Find That Text Reports`. Use **Choose Folder** in the app to pick another location, or **Use Downloads** to restore the default. The choice is remembered for future runs, including Super Speed Run. The CLI uses the same default and accepts `--output` to choose another folder.

The HTML report shows elapsed scan time, and `raw_detections.json` records it in seconds. The app also shows elapsed time when a scan completes.
Click an evidence thumbnail or **Open screenshot** in the HTML report, or **Open frame** in `report.xlsx`, to view the saved frame without opening the film. `report.html` and the spreadsheet depend on the neighboring `screenshots/` folder, so keep the full report folder together when moving those files. A CSV opened by itself contains screenshot paths, not clickable links.

To send one file to a coworker, use **Export HTML** in the app or send `shareable_report.html` from the report folder. It embeds review-size evidence frames and works without the film or any adjacent files, including for the image viewer and search. It may still be large for a feature-length scan. For original-resolution images and spreadsheet links, compress and share the whole report folder instead. Exported HTML includes frames from the video, so review it before sending it outside your team. Super Speed Run's `dialogue_gaps.html` is also standalone.

Super Speed Run writes only the two dialogue-gap files. It does not identify on-screen text.

## Performance Target

The fastest pipeline targets a two-hour feature in two hours or less on supported Apple Silicon hardware. Actual time depends on the Mac, source codec, dialogue density, and detected text volume. Full-feature benchmarking remains part of release validation; the app does not present a guaranteed completion time.

## Privacy

All normal scanning is local. Videos, caption files, screenshots, OCR results, filenames, and reports are not uploaded by Find That Text. See [PRIVACY.md](PRIVACY.md).

The logo source is `packaging/logo-source.png`. Run `python scripts/build_icons.py` on macOS after replacing it to regenerate the app and website icons.

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
find-that-text scan "/path/to/movie.mov" --scan-during-dialogue
find-that-text scan "/path/to/movie.mov" --mode adaptive --scene-detection
find-that-text scan "/path/to/movie.mov" --no-ocr-reuse
find-that-text scan "/path/to/movie.mov" --mode custom --custom-frame-step 7 --review-breadth 0.35
find-that-text scan "/path/to/movie.mov" --captions "/path/to/movie.en.srt" --minimum-gap-seconds 2
find-that-text gaps "/path/to/movie.mov" --captions "/path/to/movie.en.srt"
```

Release builds bundle the PP-OCRv6 small models. On first launch, the app copies those models into `~/Library/Application Support/Find That Text/PaddleX`; normal scans do not need internet access.

## Core Technology

- Video decoding: [FFmpeg](https://ffmpeg.org/) through [PyAV 18.1.0](https://github.com/PyAV-Org/PyAV)
- OCR: [PaddleOCR 3.7.0](https://github.com/PaddlePaddle/PaddleOCR) with PP-OCRv6 small detection and recognition models
- Optional scene-change detection: [PySceneDetect 0.7.1](https://github.com/Breakthrough/PySceneDetect)
- Mac interface: [PySide6 6.11.2](https://doc.qt.io/qtforpython-6/)
- Word plausibility: [wordfreq 3.1.1](https://github.com/rspeer/wordfreq), using offline English and Spanish small word lists

## Packaging

```bash
scripts/build_macos.sh
scripts/package_dmg.sh
```

The build creates a PyInstaller `.app` bundle and an Apple Silicon DMG. Signing and notarization are used when Apple Developer credentials are provided. Unsigned builds may require macOS **Open** or **Open Anyway**.

## License

Find That Text is released under the MIT License. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for dependency license notes.
