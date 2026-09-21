from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from find_that_text.tracking.events import TextEvent
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
) -> None:
    rows = "\n".join(_event_row(event) for event in events)
    scan_end = scan_end_seconds if scan_end_seconds is not None else metadata.duration_seconds
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Find That Text Report - {escape(metadata.filename)}</title>
  <style>
    :root {{ color-scheme: light dark; --accent: #0f766e; --border: #d6d8dc; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.45; }}
    header {{ padding: 28px 32px 18px; border-bottom: 1px solid var(--border); }}
    main {{ padding: 22px 32px 40px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    .meta {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 8px 18px; margin-top: 14px; color: #58606a; }}
    .toolbar {{ display: flex; gap: 12px; align-items: center; margin: 0 0 16px; }}
    input {{ width: min(420px, 100%); padding: 9px 11px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid var(--border); padding: 9px 10px; text-align: left; vertical-align: top; }}
    th {{ position: sticky; top: 0; background: Canvas; cursor: pointer; white-space: nowrap; }}
    td.text {{ max-width: 360px; overflow-wrap: anywhere; }}
    img.thumb {{ width: 128px; height: 72px; object-fit: cover; border-radius: 6px; border: 1px solid var(--border); }}
    .empty {{ padding: 28px; border: 1px solid var(--border); border-radius: 8px; }}
  </style>
</head>
<body>
  <header>
    <h1>Find That Text Report</h1>
    <div>{escape(metadata.filename)}</div>
    <section class="meta">
      <div><strong>Duration</strong><br>{format_timestamp(metadata.duration_seconds)}</div>
      <div><strong>Resolution</strong><br>{metadata.width} x {metadata.height}</div>
      <div><strong>Scan Mode</strong><br>{escape(scan_mode.name)} ({escape(scan_mode.description)})</div>
      <div><strong>Scan Range</strong><br>{format_timestamp(scan_start_seconds)} to {format_timestamp(scan_end)}</div>
      <div><strong>OCR Model</strong><br>{escape(ocr_model)}</div>
      <div><strong>Text Strictness</strong><br>Minimum confidence {min_ocr_confidence:.0%}</div>
      <div><strong>Application Version</strong><br>{escape(__version__)}</div>
      <div><strong>Scan Date</strong><br>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
      <div><strong>Detected Events</strong><br>{len(events)}</div>
    </section>
  </header>
  <main>
    <div class="toolbar">
      <input id="search" type="search" placeholder="Search detected text">
    </div>
    {_table(rows) if events else '<div class="empty">No visible text events were detected at the selected sampling interval.</div>'}
  </main>
  <script>
    const search = document.getElementById('search');
    const table = document.querySelector('table');
    if (search && table) {{
      search.addEventListener('input', () => {{
        const query = search.value.toLowerCase();
        for (const row of table.tBodies[0].rows) {{
          row.hidden = !row.textContent.toLowerCase().includes(query);
        }}
      }});
      for (const th of table.tHead.rows[0].cells) {{
        th.addEventListener('click', () => sortTable(th.cellIndex));
      }}
    }}
    function sortTable(index) {{
      const tbody = table.tBodies[0];
      const rows = Array.from(tbody.rows);
      const direction = table.dataset.sortIndex == index && table.dataset.sortDir !== 'desc' ? -1 : 1;
      rows.sort((a, b) => a.cells[index].textContent.localeCompare(b.cells[index].textContent, undefined, {{ numeric: true }}) * direction);
      rows.forEach(row => tbody.appendChild(row));
      table.dataset.sortIndex = index;
      table.dataset.sortDir = direction === 1 ? 'asc' : 'desc';
    }}
  </script>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def _table(rows: str) -> str:
    return f"""<table>
  <thead>
    <tr>
      <th>Start</th>
      <th>End</th>
      <th>Text</th>
      <th>Confidence</th>
      <th>Position</th>
      <th>Class</th>
      <th>Count</th>
      <th>Evidence</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>"""


def _event_row(event: TextEvent) -> str:
    thumb = ""
    if event.screenshot:
        thumb = (
            f'<a href="{escape(event.screenshot)}"><img class="thumb" '
            f'src="{escape(event.screenshot)}" alt="Evidence frame"></a>'
        )
    return f"""<tr>
  <td>{format_timestamp(event.start_seconds)}</td>
  <td>{format_timestamp(event.end_seconds)}</td>
  <td class="text">{escape(event.text)}</td>
  <td>{event.maximum_confidence:.3f}</td>
  <td>{escape(event.position)}</td>
  <td>{escape(event.classification)}</td>
  <td>{len(event.detections)}</td>
  <td>{thumb}</td>
</tr>"""
