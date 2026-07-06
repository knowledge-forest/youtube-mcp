"""Data models passed across the core/adapter boundary.

Core returns these dataclasses; adapters format them (CLI -> text, MCP -> json).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Segment:
    """One caption cue."""

    text: str
    start: float  # seconds
    duration: float  # seconds


@dataclass
class Transcript:
    video_id: str
    segments: list[Segment]
    source: str  # transcript-api | yt-dlp-auto | yt-dlp-manual
    language: str | None = None

    @property
    def text(self) -> str:
        """Plain text, one cue per line. Cleaning happens later (P1)."""
        return "\n".join(s.text for s in self.segments if s.text)

    @property
    def word_count(self) -> int:
        return sum(len(s.text.split()) for s in self.segments)


@dataclass
class Info:
    video_id: str
    title: str
    duration: int | None  # seconds
    has_captions: bool
    chapters: list[dict] = field(default_factory=list)
