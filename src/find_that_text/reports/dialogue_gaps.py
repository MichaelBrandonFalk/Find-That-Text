from __future__ import annotations

import csv
from html import escape
from pathlib import Path

from find_that_text.captions import CaptionCue, CaptionTimeline
from find_that_text.util.timestamps import format_timestamp
from find_that_text.video.metadata import VideoMetadata


def write_dialogue_gap_reports(
    output_dir: Path,
    *,
    metadata: VideoMetadata,
    timeline: CaptionTimeline,
    gaps: list[CaptionCue],
    ocr_performed: bool,
) -> tuple[Path, Path]:
    csv_path = output_dir / "dialogue_gaps.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("start", "end", "duration_seconds"))
        for gap in gaps:
            writer.writerow(
                (
                    format_timestamp(gap.start_seconds),
                    format_timestamp(gap.end_seconds),
                    f"{gap.end_seconds - gap.start_seconds:.3f}",
                )
            )

    rows = "\n".join(
        "<tr>"
        f"<td>{format_timestamp(gap.start_seconds)}</td>"
        f"<td>{format_timestamp(gap.end_seconds)}</td>"
        f"<td>{gap.end_seconds - gap.start_seconds:.1f}s</td>"
        "</tr>"
        for gap in gaps
    )
    if not rows:
        rows = '<tr><td colspan="3">No dialogue gaps in the selected range.</td></tr>'
    html_path = output_dir / "dialogue_gaps.html"
    html_path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dialogue Gaps - {escape(metadata.filename)}</title>
  <style>
    body {{ margin: 0; background: #f5f8fb; color: #24354c; font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ max-width: 900px; margin: auto; padding: 30px 22px 60px; }}
    h1 {{ margin: 0 0 6px; font-size: 28px; }}
    .muted {{ color: #607086; }}
    .summary {{ display: flex; flex-wrap: wrap; gap: 12px 28px; padding: 18px 0; border-bottom: 1px solid #d9e2eb; }}
    .summary strong {{ display: block; font-size: 22px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: white; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #d9e2eb; }}
    th {{ background: #eaf1f5; }}
    a {{ color: #14705c; }}
  </style>
</head>
<body><main>
  <h1>Dialogue Gaps</h1>
  <div class="muted">{escape(metadata.filename)} | {escape(timeline.path.name)}</div>
  <div class="summary">
    <div><strong>{len(gaps)}</strong>gap ranges</div>
    <div><strong>{format_timestamp(sum(gap.end_seconds - gap.start_seconds for gap in gaps))}</strong>available scan time</div>
    <div><strong>{timeline.non_dialogue_cue_count}</strong>music or sound cues kept in scan time</div>
  </div>
  <p class="muted">Recognized music and sound-only cues remain available for scanning. Cues mixing speech with sounds count as dialogue. Review ambiguous caption cues before relying on these ranges.</p>
  <p class="muted">{'For OCR results, see report.html.' if ocr_performed else 'No video frames were decoded and no OCR was run.'} <a href="dialogue_gaps.csv">Download CSV</a></p>
  <table><thead><tr><th>Start</th><th>End</th><th>Duration</th></tr></thead><tbody>{rows}</tbody></table>
</main></body></html>
""",
        encoding="utf-8",
    )
    return html_path, csv_path
