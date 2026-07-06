"""CLI adapter — thin. Parse args, call core, format output.

P0 commands:
    yt-core transcript URL   -> write clean file, print path + preview
    yt-core info URL         -> title, duration, chapters, captions
"""

from __future__ import annotations

import argparse
import os
import sys

from .fetch import FetchError, fetch_transcript, get_info

CACHE_ROOT = os.path.join(
    os.path.expanduser("~"), ".cache", "yt-core"
)  # cache.py will own this in P1

PREVIEW_WORDS = 200


def _cache_path(video_id: str) -> str:
    d = os.path.join(CACHE_ROOT, video_id)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "transcript.txt")


def _cmd_transcript(args: argparse.Namespace) -> int:
    langs = args.lang.split(",") if args.lang else None
    tr = fetch_transcript(args.url, languages=langs)

    path = _cache_path(tr.video_id)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(tr.text)

    words = tr.text.split()
    preview = " ".join(words[:PREVIEW_WORDS])
    if len(words) > PREVIEW_WORDS:
        preview += " …"

    print(f"video_id : {tr.video_id}")
    print(f"source   : {tr.source}")
    print(f"language : {tr.language}")
    print(f"words    : {tr.word_count}")
    print(f"path     : {path}")
    print("preview  :")
    print(preview)
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    info = get_info(args.url)
    print(f"video_id     : {info.video_id}")
    print(f"title        : {info.title}")
    print(f"duration     : {info.duration}s")
    print(f"has_captions : {info.has_captions}")
    print(f"chapters     : {len(info.chapters)}")
    for ch in info.chapters:
        print(f"  - {ch.get('start_time', 0):>7.0f}s  {ch.get('title', '')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="yt-core", description="YouTube watch engine.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_tr = sub.add_parser("transcript", help="fetch clean transcript to a file")
    p_tr.add_argument("url")
    p_tr.add_argument("--lang", help="comma-separated language codes (default: en)")
    p_tr.set_defaults(func=_cmd_transcript)

    p_info = sub.add_parser("info", help="video metadata + caption availability")
    p_info.add_argument("url")
    p_info.set_defaults(func=_cmd_info)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
