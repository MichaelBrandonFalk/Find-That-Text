from __future__ import annotations

import base64
from io import BytesIO
from datetime import datetime
from html import escape
from pathlib import Path

from PIL import Image

from find_that_text.tracking.events import TextEvent
from find_that_text.tracking.relevance import (
    BACKGROUND,
    LIKELY_FORCED_TEXT,
    NEEDS_REVIEW,
    bucket_counts,
)
from find_that_text.util.timestamps import format_timestamp
from find_that_text.version import __version__
from find_that_text.video.metadata import VideoMetadata
from find_that_text.video.sampling import ScanMode


def write_html_report(
    path: Path,
    *,
    events: list[TextEvent],
    metadata: VideoMetadata,
    scan_mode: ScanMode,
    ocr_model: str,
    scan_start_seconds: float = 0.0,
    scan_end_seconds: float | None = None,
    min_ocr_confidence: float = 0.0,
    review_breadth: float = 0.5,
    caption_path: Path | None = None,
    dialogue_optimization: bool = False,
    dialogue_gaps_only: bool = False,
    scene_detection: bool = False,
    ocr_frames: int = 0,
    reused_frames: int = 0,
    gap_report: bool = False,
    minimum_dialogue_gap_seconds: float | None = None,
    elapsed_seconds: float = 0.0,
    standalone: bool = False,
) -> None:
    scan_end = scan_end_seconds if scan_end_seconds is not None else metadata.duration_seconds
    counts = bucket_counts(events)
    caption_label = caption_path.name if caption_path else "None (uniform scan)"
    scan_scope = (
        "Dialogue gaps only"
        if dialogue_gaps_only
        else "Full video (no captions available)" if caption_path is None else "Full video"
    )
    viewer_html = (
        '<dialog id="frame-viewer"><button type="button" id="close-frame">Close</button>'
        '<img alt="Expanded evidence frame"></dialog>'
        if standalone else ""
    )
    viewer_script = """
    const viewer = document.getElementById('frame-viewer');
    document.querySelectorAll('.frame-trigger').forEach(button => button.addEventListener('click', () => {
      viewer.querySelector('img').src = button.querySelector('img').src;
      viewer.showModal();
    }));
    document.getElementById('close-frame').addEventListener('click', () => viewer.close());
    """ if standalone else ""
    sections = "\n".join(
        (
            _bucket_section(
                LIKELY_FORCED_TEXT, events, css_class="likely", report_dir=path.parent,
                standalone=standalone,
            ),
            _bucket_section(
                NEEDS_REVIEW, events, css_class="review", report_dir=path.parent,
                standalone=standalone,
            ),
            _background_section(events, report_dir=path.parent, standalone=standalone),
        )
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Find That Text Report - {escape(metadata.filename)}</title>
  <style>
    :root {{ color-scheme: light; --ink: #24354c; --muted: #607086; --line: #d9e2eb; --likely: #14705c; --review: #9a6517; --soft: #f5f8fb; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; color: var(--ink); background: white; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.45; }}
    header {{ padding: 28px max(24px, calc((100vw - 1320px) / 2)); border-bottom: 1px solid var(--line); background: #f1f7fb; }}
    main {{ padding: 24px max(24px, calc((100vw - 1320px) / 2)) 48px; }}
    h1 {{ margin: 0 0 6px; font-size: 28px; letter-spacing: 0; }}
    h2 {{ margin: 0; font-size: 21px; letter-spacing: 0; }}
    .filename {{ color: var(--muted); overflow-wrap: anywhere; }}
    .summary {{ display: grid; grid-template-columns: repeat(3, minmax(150px, 1fr)); gap: 1px; margin: 22px 0 0; border: 1px solid var(--line); background: var(--line); }}
    .summary div {{ padding: 14px 16px; background: white; }}
    .summary strong {{ display: block; font-size: 24px; }}
    .meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(205px, 1fr)); gap: 9px 20px; margin-top: 18px; color: var(--muted); font-size: 14px; }}
    .toolbar {{ position: sticky; top: 0; z-index: 3; padding: 12px 0; background: rgba(255, 255, 255, 0.96); }}
    input {{ width: min(460px, 100%); padding: 10px 12px; border: 1px solid var(--line); border-radius: 6px; color: var(--ink); background: white; font-size: 14px; }}
    .bucket {{ margin-top: 28px; }}
    .bucket-heading {{ display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-bottom: 10px; }}
    .bucket-heading span {{ color: var(--muted); }}
    details {{ margin-top: 28px; border-top: 1px solid var(--line); padding-top: 18px; }}
    summary {{ cursor: pointer; font-size: 20px; font-weight: 700; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 7px; }}
    table {{ width: 100%; min-width: 980px; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 10px; text-align: left; vertical-align: top; }}
    tr:last-child td {{ border-bottom: 0; }}
    th {{ background: var(--soft); white-space: nowrap; }}
    td.text {{ max-width: 330px; overflow-wrap: anywhere; font-weight: 650; }}
    td.reasons {{ max-width: 280px; color: var(--muted); }}
    .score {{ font-variant-numeric: tabular-nums; font-weight: 750; }}
    .likely .score {{ color: var(--likely); }}
    .review .score {{ color: var(--review); }}
    img.thumb {{ width: 160px; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 5px; border: 1px solid var(--line); }}
    .evidence-link {{ display: block; margin-top: 4px; color: #165ea8; font-weight: 650; white-space: nowrap; }}
    .frame-trigger {{ padding: 0; border: 0; background: none; color: inherit; text-align: left; cursor: pointer; font: inherit; }}
    dialog {{ width: min(96vw, 1400px); max-height: 96vh; padding: 12px; border: 1px solid var(--line); border-radius: 7px; }}
    dialog::backdrop {{ background: rgba(15, 26, 42, 0.78); }}
    dialog img {{ display: block; width: 100%; max-height: calc(96vh - 65px); object-fit: contain; }}
    dialog button {{ display: block; margin: 0 0 10px auto; padding: 6px 12px; }}
    .empty {{ padding: 24px; border: 1px solid var(--line); border-radius: 7px; color: var(--muted); }}
    @media (max-width: 720px) {{ .summary {{ grid-template-columns: 1fr; }} header, main {{ padding-left: 18px; padding-right: 18px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Forced Text Candidate Report</h1>
    <div class="filename">{escape(metadata.filename)}</div>
    <section class="summary">
      <div><strong>{counts[LIKELY_FORCED_TEXT]}</strong>Likely Forced Text</div>
      <div><strong>{counts[NEEDS_REVIEW]}</strong>Needs Review</div>
      <div><strong>{counts[BACKGROUND]}</strong>Less Likely</div>
    </section>
    <section class="meta">
      <div><strong>Video Duration</strong><br>{format_timestamp(metadata.duration_seconds)}</div>
      <div><strong>Scan Time</strong><br>{format_timestamp(elapsed_seconds)}</div>
      <div><strong>Resolution</strong><br>{metadata.width} x {metadata.height}</div>
      <div><strong>Scan Mode</strong><br>{escape(scan_mode.name)} ({escape(scan_mode.description)})</div>
      <div><strong>Scan Range</strong><br>{format_timestamp(scan_start_seconds)} to {format_timestamp(scan_end)}</div>
      <div><strong>Dialogue Captions</strong><br>{escape(caption_label)}</div>
      <div><strong>Scan Scope</strong><br>{escape(scan_scope)}</div>
      {f'<div><strong>Minimum Dialogue Gap</strong><br>{minimum_dialogue_gap_seconds:g} s</div>' if minimum_dialogue_gap_seconds is not None else ''}
      {('<div><strong>Dialogue Gaps</strong><br><a href="dialogue_gaps.html">View gap timeline</a> | <a href="dialogue_gaps.csv">CSV</a></div>' if gap_report and not standalone else '')}
      <div><strong>Adaptive Cadence</strong><br>{"On" if dialogue_optimization else "Off"}</div>
      <div><strong>Scene Detection</strong><br>{"On" if scene_detection else "Off"}</div>
      <div><strong>Review Breadth</strong><br>{review_breadth:.0%}</div>
      <div><strong>OCR Model</strong><br>{escape(ocr_model)}</div>
      <div><strong>OCR Work</strong><br>{ocr_frames} frames analyzed, {reused_frames} reused</div>
      <div><strong>Text Strictness</strong><br>Minimum confidence {min_ocr_confidence:.0%}</div>
      <div><strong>Application Version</strong><br>{escape(__version__)}</div>
      {('<div><strong>Review Files</strong><br><a href="report.xlsx">Spreadsheet</a> | <a href="report.csv">CSV</a></div>' if not standalone else '')}
      <div><strong>Scan Date</strong><br>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
    </section>
  </header>
  <main>
    <div class="toolbar"><input id="search" type="search" placeholder="Search text, reasons, or timecodes"></div>
    {sections}
  </main>
  {viewer_html}
  <script>
    const search = document.getElementById('search');
    search.addEventListener('input', () => {{
      const query = search.value.toLowerCase();
      for (const row of document.querySelectorAll('tbody tr')) {{
        row.hidden = !row.textContent.toLowerCase().includes(query);
      }}
      if (query) document.querySelectorAll('details').forEach(item => item.open = true);
    }});
    {viewer_script}
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def _bucket_section(
    bucket: str, events: list[TextEvent], *, css_class: str, report_dir: Path, standalone: bool
) -> str:
    matching = [event for event in events if event.review_bucket == bucket]
    content = (
        _table(matching, css_class=css_class, report_dir=report_dir, standalone=standalone)
        if matching else '<div class="empty">No moments in this section.</div>'
    )
    return f"""<section class="bucket {css_class}">
      <div class="bucket-heading"><h2>{escape(bucket)}</h2><span>{len(matching)} moments</span></div>
      {content}
    </section>"""


def _background_section(events: list[TextEvent], *, report_dir: Path, standalone: bool) -> str:
    matching = [event for event in events if event.review_bucket == BACKGROUND]
    content = (
        _table(matching, css_class="background", report_dir=report_dir, standalone=standalone)
        if matching else '<div class="empty">No moments in this section.</div>'
    )
    return f"""<details>
      <summary>{escape(BACKGROUND)} ({len(matching)})</summary>
      <div class="bucket background">{content}</div>
    </details>"""


def _table(events: list[TextEvent], *, css_class: str, report_dir: Path, standalone: bool) -> str:
    rows = "\n".join(
        _event_row(event, report_dir=report_dir, standalone=standalone) for event in events
    )
    return f"""<div class="table-wrap"><table class="{escape(css_class)}">
      <thead><tr><th>Start</th><th>End</th><th>Text</th><th>Score</th><th>Why</th><th>Position</th><th>Evidence</th></tr></thead>
      <tbody>{rows}</tbody>
    </table></div>"""


def _event_row(event: TextEvent, *, report_dir: Path, standalone: bool) -> str:
    thumb = ""
    if event.screenshot:
        if standalone:
            image_src = _embedded_image(report_dir, event.screenshot)
            if image_src:
                thumb = (
                    '<button class="frame-trigger" type="button">'
                    f'<img class="thumb" src="{image_src}" '
                    f'alt="Evidence frame for event {event.event_id}">'
                    '<span class="evidence-link">Open screenshot</span></button>'
                )
        else:
            thumb = (
                f'<a href="{escape(event.screenshot, quote=True)}" target="_blank" rel="noopener">'
                f'<img class="thumb" src="{escape(event.screenshot, quote=True)}" '
                f'alt="Evidence frame for event {event.event_id}"></a>'
                f'<a class="evidence-link" href="{escape(event.screenshot, quote=True)}" '
                f'target="_blank" rel="noopener">Open screenshot</a>'
            )
    return f"""<tr>
      <td>{format_timestamp(event.start_seconds)}</td>
      <td>{format_timestamp(event.end_seconds)}</td>
      <td class="text">{escape(event.text)}</td>
      <td class="score">{event.relevance_score:.0%}</td>
      <td class="reasons">{escape("; ".join(event.relevance_reasons))}</td>
      <td>{escape(event.position)}</td>
      <td>{thumb}</td>
    </tr>"""


def _embedded_image(report_dir: Path, screenshot: str) -> str:
    image_path = (report_dir / screenshot).resolve()
    if not image_path.is_relative_to(report_dir.resolve()) or not image_path.is_file():
        return ""
    try:
        with Image.open(image_path) as source:
            image = source.convert("RGB")
            image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=80)
    except OSError:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
