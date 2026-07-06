"""Disk cache — keyed by video id under ~/.cache/youtube-mcp/<id>/.

Files:
    segments.json   cleaned segments + source/language (source of truth)
    transcript.txt  cleaned prose (for humans / native Read)
"""

from __future__ import annotations

import json
import os

from .models import Segment, Transcript

CACHE_ROOT = os.path.join(os.path.expanduser("~"), ".cache", "youtube-mcp")


def cache_dir(video_id: str) -> str:
    d = os.path.join(CACHE_ROOT, video_id)
    os.makedirs(d, exist_ok=True)
    return d


def _segments_path(video_id: str) -> str:
    return os.path.join(cache_dir(video_id), "segments.json")


def transcript_path(video_id: str) -> str:
    return os.path.join(cache_dir(video_id), "transcript.txt")


def load(video_id: str) -> Transcript | None:
    path = _segments_path(video_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    segments = [Segment(**s) for s in data["segments"]]
    return Transcript(video_id, segments, data["source"], data.get("language"))


def store(tr: Transcript) -> str:
    payload = {
        "source": tr.source,
        "language": tr.language,
        "segments": [vars(s) for s in tr.segments],
    }
    with open(_segments_path(tr.video_id), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    txt = transcript_path(tr.video_id)
    with open(txt, "w", encoding="utf-8") as fh:
        fh.write(tr.text)
    return txt
