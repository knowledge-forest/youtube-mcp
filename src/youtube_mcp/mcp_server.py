"""MCP adapter — thin. Exposes 4 pull-based tools over the core engine.

Design: tools return paths, previews, and timestamped snippets — never a full
transcript dump — so long videos don't flood the client's context.

Run: yt-mcp serve   (stdio transport)
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .chunk import get_segment as _get_segment
from .chunk import search_transcript as _search_transcript
from .fetch import get_info as _get_info
from .service import get_transcript as _get_transcript

mcp = FastMCP("youtube")

PREVIEW_WORDS = 200


@mcp.tool()
def get_info(url: str) -> dict:
    """Cheap probe of a YouTube video: title, duration, chapters, caption availability.

    Call this first to decide whether to fetch a transcript and how to read it.
    """
    info = _get_info(url)
    return {
        "video_id": info.video_id,
        "title": info.title,
        "duration_seconds": info.duration,
        "has_captions": info.has_captions,
        "chapters": info.chapters,
    }


@mcp.tool()
def get_transcript(url: str, lang: str | None = None) -> dict:
    """Fetch a cleaned transcript and write it to a local file.

    Returns the file path plus a short preview and stats — NOT the full text.
    Read the file, or use search_transcript / get_segment, to pull detail on demand.
    """
    from . import cache

    langs = lang.split(",") if lang else None
    tr = _get_transcript(url, languages=langs)
    words = tr.text.split()
    preview = " ".join(words[:PREVIEW_WORDS])
    if len(words) > PREVIEW_WORDS:
        preview += " …"
    return {
        "video_id": tr.video_id,
        "source": tr.source,
        "language": tr.language,
        "word_count": tr.word_count,
        "path": cache.transcript_path(tr.video_id),
        "preview": preview,
    }


@mcp.tool()
def search_transcript(url: str, query: str, lang: str | None = None) -> list[dict]:
    """Find cues matching a query. Returns timestamped snippets only.

    Use for long videos: locate the relevant moments without loading everything.
    """
    langs = lang.split(",") if lang else None
    hits = _search_transcript(url, query, languages=langs)
    return [{"timestamp": h.timestamp, "start_seconds": h.start, "text": h.text} for h in hits]


@mcp.tool()
def get_segment(url: str, start: float, end: float, lang: str | None = None) -> dict:
    """Return transcript text for the time range [start, end) in seconds."""
    langs = lang.split(",") if lang else None
    text = _get_segment(url, start, end, languages=langs)
    return {"start_seconds": start, "end_seconds": end, "text": text}


def serve() -> None:
    mcp.run()  # stdio transport by default
