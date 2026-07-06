"""Fetch layer: id parsing, VTT parsing, and fallback-chain ordering (no network)."""

from __future__ import annotations

import pytest

from youtube_mcp import fetch
from youtube_mcp.fetch import FetchError, extract_video_id
from youtube_mcp.models import Segment, Transcript


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ&t=42s",
        "dQw4w9WgXcQ",
    ],
)
def test_extract_video_id(url):
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extract_video_id_rejects_garbage():
    with pytest.raises(FetchError):
        extract_video_id("https://example.com/not-a-video")


def test_parse_vtt(tmp_path):
    vtt = tmp_path / "x.en.vtt"
    vtt.write_text(
        "WEBVTT\n"
        "Kind: captions\n"
        "Language: en\n\n"
        "00:00:01.000 --> 00:00:03.000\n"
        "<c>hello</c> world\n\n"
        "00:00:03.000 --> 00:00:05.000\n"
        "second line\n",
        encoding="utf-8",
    )
    segs = fetch._parse_vtt(str(vtt))
    assert [s.text for s in segs] == ["hello world", "second line"]
    assert segs[0].start == 1.0
    assert segs[0].duration == 2.0


# --- fallback-chain ordering ----------------------------------------------
def _stub_transcript(source):
    return Transcript("vid", [Segment("t", 0.0, 1.0)], source, "en")


def test_chain_uses_first_success(monkeypatch):
    monkeypatch.setattr(fetch, "_from_transcript_api", lambda v, l: _stub_transcript("transcript-api"))
    monkeypatch.setattr(fetch, "_from_ytdlp_auto", lambda v, l: pytest.fail("should not reach auto"))
    tr = fetch.fetch_transcript("dQw4w9WgXcQ")
    assert tr.source == "transcript-api"


def test_chain_falls_through_to_manual(monkeypatch):
    monkeypatch.setattr(fetch, "_from_transcript_api", lambda v, l: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(fetch, "_from_ytdlp_auto", lambda v, l: None)  # empty result
    monkeypatch.setattr(fetch, "_from_ytdlp_manual", lambda v, l: _stub_transcript("yt-dlp-manual"))
    tr = fetch.fetch_transcript("dQw4w9WgXcQ")
    assert tr.source == "yt-dlp-manual"


def test_chain_all_fail_raises(monkeypatch):
    monkeypatch.setattr(fetch, "_from_transcript_api", lambda v, l: None)
    monkeypatch.setattr(fetch, "_from_ytdlp_auto", lambda v, l: None)
    monkeypatch.setattr(fetch, "_from_ytdlp_manual", lambda v, l: (_ for _ in ()).throw(RuntimeError("nope")))
    with pytest.raises(FetchError):
        fetch.fetch_transcript("dQw4w9WgXcQ")
