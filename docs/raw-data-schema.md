# Raw Detection JSON Schema

`raw_detections.json` schema version 2 stores an audit trail of every OCR detection used to create the grouped report.

Top-level fields:

- `schema_version`: integer schema version.
- `application` and `application_version`: generator metadata.
- `source`: filename, duration, resolution, codec, and frame-rate metadata.
- `scan`: scan mode, frame step or interval, range, review breadth, caption filename, whether only dialogue gaps were scanned, adaptive cadence, scene-change times, OCR model/backend description, and analyzed/reused OCR frame counts.
- `events`: grouped moment summaries with relevance score, review bucket, scoring reasons, dialogue-gap ratio, classification flags, and references to raw detection indexes.
- `detections`: all raw OCR detections.

Each detection contains:

- `timestamp_seconds`
- `timestamp` formatted as `HH:MM:SS.mmm`
- `text`
- `confidence`
- `detector_confidence`
- `polygon`
- `box` with `x`, `y`, `width`, `height`
- `frame_width`
- `frame_height`
- `frame_index`
- `source_filename`
- `position`

The raw detections are intentionally not filtered by event grouping. If grouping is wrong, this file should still contain the underlying OCR observations needed to investigate.
