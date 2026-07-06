"""Tier-1 cleaning — strip markup/noise and collapse rolling-caption overlap.

Rolling-caption overlap is the biggest source of token bloat in YouTube
auto-captions: each cue re-shows the tail of the previous cue plus a few new
words (a scrolling window). We keep only the NEW words per cue, preserving the
onset timestamp so search/segment stay accurate.
"""

from __future__ import annotations

import html
import re

from .models import Segment, Transcript

_TAG_RE = re.compile(r"<[^>]+>")
_NOISE_RE = re.compile(r"\[[^\]]*\]")  # [Music], [Applause], [ __ ]
_WS_RE = re.compile(r"\s+")


def clean_text(s: str) -> str:
    s = _TAG_RE.sub("", s)
    s = html.unescape(s)
    s = _NOISE_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()


def _new_words(prev: str, cur: str) -> str:
    """Return only the words in `cur` not already covered by the tail of `prev`.

    Finds the largest k where prev's last k words == cur's first k words, then
    drops those k words from cur. Handles the scrolling-window duplication.
    """
    pw = prev.split()
    cw = cur.split()
    max_ov = min(len(pw), len(cw))
    for k in range(max_ov, 0, -1):
        if pw[-k:] == cw[:k]:
            return " ".join(cw[k:])
    return cur


def dedup_segments(segments: list[Segment]) -> list[Segment]:
    out: list[Segment] = []
    prev_full = ""
    for seg in segments:
        text = clean_text(seg.text)
        if not text:
            continue
        if text == prev_full:
            continue  # exact consecutive duplicate
        new_part = _new_words(prev_full, text) if prev_full else text
        prev_full = text
        new_part = new_part.strip()
        if not new_part:
            continue  # fully contained in previous cue
        out.append(Segment(text=new_part, start=seg.start, duration=seg.duration))
    return out


def clean_transcript(tr: Transcript) -> Transcript:
    return Transcript(
        video_id=tr.video_id,
        segments=dedup_segments(tr.segments),
        source=tr.source,
        language=tr.language,
    )
