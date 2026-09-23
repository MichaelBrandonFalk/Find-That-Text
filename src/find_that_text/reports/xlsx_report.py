from __future__ import annotations

from pathlib import Path

import xlsxwriter

from find_that_text.reports.csv_report import CSV_COLUMNS
from find_that_text.tracking.events import TextEvent


REVIEW_COLUMNS = [
    "Detected Text",
    "Start Time",
    "End Time",
    "Relevance Score",
    "Review Bucket",
    "Evidence Screenshot",
    "Annotated Screenshot",
    "Event ID",
    *(column for column in CSV_COLUMNS if column not in {
        "Detected Text", "Start Time", "End Time", "Relevance Score",
        "Review Bucket", "Evidence Screenshot", "Annotated Screenshot", "Event ID",
    }),
]

NUMERIC_COLUMNS = {
    "Event ID",
    "Average Confidence",
    "Maximum Confidence",
    "Detector Confidence",
    "Relevance Score",
    "Dialogue-Free Ratio",
    "Detection Count",
}
SCREENSHOT_COLUMNS = {"Evidence Screenshot", "Annotated Screenshot"}


def write_xlsx_report(path: Path, events: list[TextEvent]) -> None:
    with xlsxwriter.Workbook(str(path), {"strings_to_formulas": False, "strings_to_urls": False}) as workbook:
        sheet = workbook.add_worksheet("Review")
        header = workbook.add_format({
            "bold": True,
            "font_color": "#FFFFFF",
            "bg_color": "#315F68",
            "valign": "vcenter",
        })
        text = workbook.add_format({"valign": "top"})
        wrapped = workbook.add_format({"valign": "top", "text_wrap": True})
        score = workbook.add_format({"valign": "top", "num_format": "0%"})
        decimal = workbook.add_format({"valign": "top", "num_format": "0.000"})
        integer = workbook.add_format({"valign": "top", "num_format": "0"})
        link = workbook.add_format({"font_color": "#165EA8", "underline": 1, "valign": "top"})

        widths = {
            "Event ID": 10,
            "Start Time": 13,
            "End Time": 13,
            "Detected Text": 40,
            "Review Bucket": 28,
            "Relevance Score": 15,
            "Evidence Screenshot": 18,
            "Annotated Screenshot": 21,
            "Why Flagged": 56,
        }
        for col, name in enumerate(REVIEW_COLUMNS):
            sheet.write_string(0, col, name, header)
            sheet.set_column(col, col, widths.get(name, 18))
        sheet.set_row(0, 28)
        sheet.freeze_panes(1, 3)

        for row, event in enumerate(events, start=1):
            values = event.to_row()
            sheet.set_row(row, 34)
            for col, name in enumerate(REVIEW_COLUMNS):
                value = values[name]
                if name in SCREENSHOT_COLUMNS:
                    if value and (path.parent / value).is_file():
                        label = "Open frame" if name == "Evidence Screenshot" else "Open annotated"
                        sheet.write_url(row, col, f"external:{value}", link, label)
                    continue
                if name in NUMERIC_COLUMNS and value:
                    number_format = (
                        score if name == "Relevance Score"
                        else integer if name in {"Event ID", "Detection Count"}
                        else decimal
                    )
                    sheet.write_number(row, col, float(value), number_format)
                else:
                    sheet.write_string(
                        row,
                        col,
                        value,
                        wrapped if name in {"Detected Text", "Review Bucket", "Why Flagged"} else text,
                    )

        sheet.autofilter(0, 0, max(1, len(events)), len(REVIEW_COLUMNS) - 1)
