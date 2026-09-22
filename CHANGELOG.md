# Changelog

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
