"""Chunk: timestamp formatting, search filtering, segment ranges (mocked transcript)."""

from __future__ import annotations

import pytest

from youtube_mcp import chunk
from youtube_mcp.models import Segment, Transcript


@pytest.fixture
def stub(monkeypatch):
    tr = Transcript(
        "vid",
        [
            Segment("intro hello", 0.0, 2.0),
            Segment("the main point", 65.0, 3.0),
            Segment("hello again", 130.0, 2.0),
        ],
        "transcript-api",
        "en",
    )
    monkeypatch.setattr(chunk, "get_transcript", lambda url, languages=None: tr)
    return tr


@pytest.mark.parametrize(
    "seconds,expected",
    [(0, "0:00"), (65, "1:05"), (600, "10:00"), (3661, "1:01:01")],
)
def test_format_timestamp(seconds, expected):
    assert chunk.format_timestamp(seconds) == expected


def test_search_is_case_insensitive_and_timestamped(stub):
    hits = chunk.search_transcript("url", "HELLO")
    assert [h.text for h in hits] == ["intro hello", "hello again"]
    assert [h.timestamp for h in hits] == ["0:00", "2:10"]


def test_search_no_match(stub):
    assert chunk.search_transcript("url", "zzz") == []


def test_get_segment_range_is_half_open(stub):
    # [0, 65) includes onset 0.0, excludes onset 65.0
    assert chunk.get_segment("url", 0, 65) == "intro hello"
    # [65, 200) includes the last two
    assert chunk.get_segment("url", 65, 200) == "the main point hello again"


def test_get_segment_empty_range(stub):
    assert chunk.get_segment("url", 300, 400) == ""
