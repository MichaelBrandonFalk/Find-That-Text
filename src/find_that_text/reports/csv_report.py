from __future__ import annotations

import csv
from pathlib import Path

from find_that_text.tracking.events import TextEvent


CSV_COLUMNS = [
    "Event ID",
    "Start Time",
    "End Time",
    "Duration",
    "Detected Text",
    "Average Confidence",
    "Maximum Confidence",
    "Position",
    "Bounding Box",
    "Detection Count",
    "Persistent",
    "Classification",
    "Evidence Screenshot",
    "Annotated Screenshot",
    "Source Filename",
]


def write_csv_report(path: Path, events: list[TextEvent]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for event in events:
            writer.writerow(event.to_row())
