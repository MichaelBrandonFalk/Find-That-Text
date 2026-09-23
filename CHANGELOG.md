# Changelog

## 1.6.1

- Ensure each eligible short dialogue gap gets a midpoint OCR sample when the regular frame cadence would otherwise miss the gap.

## 1.6.0

- Added an adjustable minimum dialogue-free break, defaulting to 1.0 second, for OCR scans and gap-only exports.
- Stopped demoting crowded readable scenes as credits solely because many text events occur nearby.
- Added offline English/Spanish word plausibility to promote readable signage and screens while keeping garbled OCR out of Likely Forced Text.
- Added elapsed processing time to the app, HTML reports, raw JSON, and CLI output.

## 1.5.0

- Built dialogue-free ranges from SRT/VTT cues before OCR; recognized music and sound-effect cues no longer block the default scan.
- Added Super Speed Run to export dialogue-gap HTML and CSV without frame decoding or OCR.
- Added the same gap timeline to normal scans with captions, plus a link from the OCR report.
- Updated the Mac interface, CLI, README, and download page to explain the two workflows.

## 1.4.0

- Added conservative OCR result reuse for near-identical sampled frames, with periodic fresh checks and a disable switch.
- Included analyzed/reused OCR frame counts in scan reports and raw JSON.
- Labeled the app and website with linked, versioned video, OCR, scene-detection, and interface components.

## 1.3.0

- Made the fastest scan the default: every 23rd frame, only outside captioned dialogue when SRT/VTT captions are available.
- Separated dialogue-gap filtering from frame cadence; full-video, adaptive, custom interval, every-frame, and scene-change options remain available.
- Skipped RGB conversion for filtered or unsampled frames and seeked to the start of a selected late-video range.
- Made caption clearing persistent for a scan and updated the app and website to explain the speed/coverage tradeoff.

## 1.2.0

- Added optional English or Spanish SRT/VTT dialogue timelines with default-on dialogue-gap optimization.
- Added adaptive recommended sampling: 0.5 seconds in quiet gaps, 2 seconds during dialogue, a 1-second no-caption fallback, and priority sampling at gap boundaries.
- Added PySceneDetect scene-change sampling without removing the regular heartbeat inside shots.
- Switched the default OCR runtime to separate PP-OCRv6 small detection and batched recognition models on 1280-pixel frames.
- Added detector confidence, temporal confirmation, text plausibility, geometry, title-card, dialogue-gap, watermark, repetition, and credits-density relevance scoring.
- Grouped nearby OCR lines into screen-text moments and divided reports into Likely Forced Text, Needs Review, and collapsed Background / Credits / Repeated Graphics sections.
- Preserved all uncertain results in CSV and raw JSON while demoting isolated symbols and persistent graphics from the primary queue.
- Captured evidence screenshots during OCR to avoid a second full video decode.
- Updated the GUI, CLI, documentation, and download page for the forced-text workflow.

## 1.1.0

- Added a custom scan mode for checking every user-selected number of frames.
- Added a Text Strictness slider for filtering uncertain OCR results by confidence.
- Added scan settings to HTML and raw JSON report metadata.

## 1.0.0

- Initial project implementation.
- Added Default mode for checking every 23rd frame and Advanced mode for checking every frame.
- Added optional start/end timestamp ranges for scanning a selected portion of a video.
