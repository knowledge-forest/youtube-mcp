"""Orchestration — cache -> fetch -> clean -> cache.

Single entry point used by every adapter and by chunk tools, so cleaning and
caching happen exactly once in one place.
"""

from __future__ import annotations

from . import cache
from .clean import clean_transcript
from .fetch import extract_video_id, fetch_transcript
from .models import Transcript


def get_transcript(
    url: str, languages: list[str] | None = None, refresh: bool = False
) -> Transcript:
    video_id = extract_video_id(url)
    if not refresh:
        cached = cache.load(video_id)
        if cached:
            return cached
    raw = fetch_transcript(url, languages)
    cleaned = clean_transcript(raw)
    cache.store(cleaned)
    return cleaned
