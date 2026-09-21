from __future__ import annotations

import re
import unicodedata


CONFUSABLES = str.maketrans(
    {
        "0": "O",
        "1": "I",
        "5": "S",
        "|": "I",
        "l": "I",
    }
)


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "")
    value = value.strip().upper()
    value = value.translate(CONFUSABLES)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"^[^\w]+|[^\w]+$", "", value)
    return value
