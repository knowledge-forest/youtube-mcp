"""Cache: round-trip store/load and miss behavior (isolated tmp dir)."""

from __future__ import annotations

import pytest

from youtube_mcp import cache
from youtube_mcp.models import Segment, Transcript


@pytest.fixture(autouse=True)
def _tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_ROOT", str(tmp_path))


def _tr():
    return Transcript(
        "abc123",
        [Segment("hello world", 0.0, 1.5), Segment("second", 1.5, 1.0)],
        "transcript-api",
        "en",
    )


def test_load_miss_returns_none():
    assert cache.load("does-not-exist") is None


def test_store_then_load_roundtrip():
    tr = _tr()
    path = cache.store(tr)

    # transcript.txt holds cleaned prose
    assert path.endswith("transcript.txt")
    with open(path, encoding="utf-8") as fh:
        assert fh.read() == "hello world second"

    loaded = cache.load("abc123")
    assert loaded is not None
    assert loaded.source == "transcript-api"
    assert loaded.language == "en"
    assert [(s.text, s.start, s.duration) for s in loaded.segments] == [
        ("hello world", 0.0, 1.5),
        ("second", 1.5, 1.0),
    ]


def test_transcript_path_is_stable():
    tr = _tr()
    cache.store(tr)
    assert cache.transcript_path("abc123").endswith("abc123/transcript.txt")
