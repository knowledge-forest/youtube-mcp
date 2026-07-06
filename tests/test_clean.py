"""Golden tests for tier-1 clean + rolling-caption dedup.

Run: uv run python tests/test_clean.py   (or: uv run pytest)
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from youtube_mcp.clean import clean_text, dedup_segments  # noqa: E402
from youtube_mcp.models import Segment  # noqa: E402


def _segs(*texts):
    return [Segment(text=t, start=float(i), duration=1.0) for i, t in enumerate(texts)]


def _texts(segs):
    return [s.text for s in segs]


def test_clean_strips_tags_noise_entities():
    assert clean_text("<c>hello</c> &amp; bye") == "hello & bye"
    assert clean_text("music here [Music] end") == "music here end"
    assert clean_text("  multi   space ") == "multi space"


def test_exact_duplicate_collapsed():
    out = dedup_segments(_segs("hello world", "hello world", "hello world"))
    assert _texts(out) == ["hello world"]


def test_growing_caption_keeps_new_words():
    out = dedup_segments(_segs("hello", "hello world", "hello world foo"))
    assert _texts(out) == ["hello", "world", "foo"]


def test_scrolling_window_overlap():
    out = dedup_segments(_segs("the quick brown", "quick brown fox", "brown fox jumps"))
    assert _texts(out) == ["the quick brown", "fox", "jumps"]
    # reconstructed prose is clean
    assert " ".join(_texts(out)) == "the quick brown fox jumps"


def test_dedup_preserves_onset_timestamp():
    segs = [
        Segment("the quick brown", start=10.0, duration=2.0),
        Segment("quick brown fox", start=12.0, duration=2.0),
    ]
    out = dedup_segments(segs)
    assert out[0].start == 10.0
    assert out[1].text == "fox"
    assert out[1].start == 12.0  # new word keeps its own cue's onset


def test_empty_and_noise_only_dropped():
    out = dedup_segments(_segs("[Music]", "", "real text", "[Applause]"))
    assert _texts(out) == ["real text"]


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")


if __name__ == "__main__":
    _run()
