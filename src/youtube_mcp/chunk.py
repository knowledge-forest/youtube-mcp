"""Pull-based reading — search and slice without loading the whole transcript.

These are what keep long videos from flooding the context: the agent greps or
takes a time range instead of pulling every word.
"""

from __future__ import annotations

from .models import Hit
from .service import get_transcript


def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def search_transcript(
    url: str, query: str, languages: list[str] | None = None
) -> list[Hit]:
    tr = get_transcript(url, languages)
    q = query.lower()
    return [
        Hit(text=s.text, start=s.start, timestamp=format_timestamp(s.start))
        for s in tr.segments
        if q in s.text.lower()
    ]


def get_segment(
    url: str, start: float, end: float, languages: list[str] | None = None
) -> str:
    """Text of all cues whose onset falls in [start, end)."""
    tr = get_transcript(url, languages)
    return " ".join(s.text for s in tr.segments if start <= s.start < end)
