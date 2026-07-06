"""Fetch layer — transcript fallback chain and video info.

Chain order (fastest -> most robust):
    1. youtube-transcript-api   (no download)
    2. yt-dlp automatic captions
    3. yt-dlp manual captions

Self-heal: yt-dlp breaks when YouTube changes its page layout; a newer yt-dlp
usually already carries the fix. On an extraction failure we upgrade yt-dlp in
place once (per process), reload it, and retry the call. ASR is deferred.
"""

from __future__ import annotations

import importlib
import os
import re
import subprocess
import sys
import tempfile

from .models import Info, Segment, Transcript

_ID_PATTERNS = [
    r"(?:v=|/shorts/|/embed/|youtu\.be/|/v/)([0-9A-Za-z_-]{11})",
    r"^([0-9A-Za-z_-]{11})$",  # bare id
]


class FetchError(RuntimeError):
    """Raised when every source in the chain fails."""


def extract_video_id(url: str) -> str:
    url = url.strip()
    for pat in _ID_PATTERNS:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    raise FetchError(f"Could not parse a video id from: {url!r}")


# --------------------------------------------------------------------------- #
# Self-heal (yt-dlp auto-update + retry)
# --------------------------------------------------------------------------- #
_healed_once = False  # process-wide guard: attempt the upgrade at most once


def _heal_ytdlp() -> bool:
    """Best-effort in-place yt-dlp upgrade + reload. True if a new module loaded."""
    global _healed_once
    if _healed_once:
        return False
    _healed_once = True
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", "yt-dlp"],
            check=True,
            capture_output=True,
            timeout=180,
        )
        import yt_dlp

        importlib.reload(yt_dlp)
        importlib.reload(yt_dlp.utils)
    except Exception:  # noqa: BLE001 - read-only env, no network, no pip: give up quietly
        return False
    return True


def _ytdlp_call(fn):
    """Run a yt-dlp operation; on an extraction failure, self-heal once and retry."""
    import yt_dlp

    try:
        return fn()
    except yt_dlp.utils.DownloadError:
        if _heal_ytdlp():
            return fn()  # re-imports the reloaded module on the retry
        raise


# --------------------------------------------------------------------------- #
# Transcript chain
# --------------------------------------------------------------------------- #
def fetch_transcript(url: str, languages: list[str] | None = None) -> Transcript:
    video_id = extract_video_id(url)
    langs = languages or ["en"]
    errors: list[str] = []

    for source in (_from_transcript_api, _from_ytdlp_auto, _from_ytdlp_manual):
        try:
            result = source(video_id, langs)
            if result and result.segments:
                return result
        except Exception as exc:  # noqa: BLE001 - collect and continue chain
            errors.append(f"{source.__name__}: {exc}")

    raise FetchError(
        "All transcript sources failed for "
        f"{video_id}:\n  " + "\n  ".join(errors)
    )


def _from_transcript_api(video_id: str, langs: list[str]) -> Transcript | None:
    """youtube-transcript-api. Supports both 1.x (fetch) and 0.6.x (get_transcript)."""
    from youtube_transcript_api import YouTubeTranscriptApi

    # 1.x instance API
    if hasattr(YouTubeTranscriptApi, "fetch") or not hasattr(
        YouTubeTranscriptApi, "get_transcript"
    ):
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=langs)
        segments = [
            Segment(text=s.text, start=s.start, duration=s.duration)
            for s in fetched
        ]
        return Transcript(video_id, segments, "transcript-api", langs[0])

    # 0.6.x classmethod API
    rows = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
    segments = [
        Segment(text=r["text"], start=r["start"], duration=r.get("duration", 0.0))
        for r in rows
    ]
    return Transcript(video_id, segments, "transcript-api", langs[0])


def _from_ytdlp_auto(video_id: str, langs: list[str]) -> Transcript | None:
    return _ytdlp_subs(video_id, langs, automatic=True)


def _from_ytdlp_manual(video_id: str, langs: list[str]) -> Transcript | None:
    return _ytdlp_subs(video_id, langs, automatic=False)


def _ytdlp_subs(video_id: str, langs: list[str], automatic: bool) -> Transcript | None:
    """Download a VTT subtitle track with yt-dlp and parse it."""
    url = f"https://www.youtube.com/watch?v={video_id}"

    def run() -> Transcript | None:
        import yt_dlp

        with tempfile.TemporaryDirectory() as tmp:
            opts = {
                "skip_download": True,
                "writesubtitles": not automatic,
                "writeautomaticsub": automatic,
                "subtitleslangs": langs,
                "subtitlesformat": "vtt",
                "outtmpl": os.path.join(tmp, "%(id)s.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            vtt = _find_vtt(tmp, langs)
            if not vtt:
                return None
            segments = _parse_vtt(vtt)

        if not segments:
            return None
        source = "yt-dlp-auto" if automatic else "yt-dlp-manual"
        return Transcript(video_id, segments, source, langs[0])

    return _ytdlp_call(run)


def _find_vtt(directory: str, langs: list[str]) -> str | None:
    files = [f for f in os.listdir(directory) if f.endswith(".vtt")]
    if not files:
        return None
    # prefer a requested language, else first
    for lang in langs:
        for f in files:
            if f".{lang}." in f:
                return os.path.join(directory, f)
    return os.path.join(directory, files[0])


_TS_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[.,](\d{3})"
)
_TAG_RE = re.compile(r"<[^>]+>")


def _parse_vtt(path: str) -> list[Segment]:
    """Minimal VTT parse. Real de-dup/clean is a later milestone (P1)."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    segments: list[Segment] = []
    start = 0.0
    duration = 0.0
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        text = " ".join(buffer).strip()
        text = _TAG_RE.sub("", text)
        if text:
            segments.append(Segment(text=text, start=start, duration=duration))
        buffer = []

    for line in lines:
        m = _TS_RE.match(line.strip())
        if m:
            flush()
            h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
            start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
            end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
            duration = max(0.0, end - start)
        elif line.strip() in ("", "WEBVTT") or line.startswith(("NOTE", "Kind:", "Language:")):
            continue
        else:
            buffer.append(line.strip())
    flush()
    return segments


# --------------------------------------------------------------------------- #
# Info
# --------------------------------------------------------------------------- #
def get_info(url: str) -> Info:
    """Cheap probe: title, duration, chapters, caption availability."""
    video_id = extract_video_id(url)

    def run():
        import yt_dlp

        opts = {"skip_download": True, "quiet": True, "no_warnings": True, "noprogress": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )

    data = _ytdlp_call(run)

    has_captions = bool(data.get("subtitles") or data.get("automatic_captions"))
    return Info(
        video_id=video_id,
        title=data.get("title", ""),
        duration=data.get("duration"),
        has_captions=has_captions,
        chapters=data.get("chapters") or [],
    )
