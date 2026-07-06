"""CLI adapter — thin. Parse args, call core, format output.

Commands:
    yt-mcp info URL              -> title, duration, chapters, captions
    yt-mcp transcript URL        -> clean transcript to file, print path + preview
    yt-mcp search URL "query"    -> timestamped matching cues
    yt-mcp segment URL START END -> text in a time range (seconds)
"""

from __future__ import annotations

import argparse
import sys

from . import cache
from .chunk import get_segment, search_transcript
from .fetch import FetchError, get_info
from .service import get_transcript

PREVIEW_WORDS = 200


def _langs(arg: str | None) -> list[str] | None:
    return arg.split(",") if arg else None


def _cmd_transcript(args: argparse.Namespace) -> int:
    tr = get_transcript(args.url, languages=_langs(args.lang), refresh=args.refresh)
    path = cache.transcript_path(tr.video_id)

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


def _cmd_search(args: argparse.Namespace) -> int:
    hits = search_transcript(args.url, args.query, languages=_langs(args.lang))
    if not hits:
        print(f"no matches for {args.query!r}")
        return 0
    for h in hits:
        print(f"[{h.timestamp}] {h.text}")
    return 0


def _cmd_segment(args: argparse.Namespace) -> int:
    text = get_segment(args.url, args.start, args.end, languages=_langs(args.lang))
    print(text or "(no cues in range)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="yt-mcp", description="YouTube watch engine.")
    sub = parser.add_subparsers(dest="command", required=True)

    lang = argparse.ArgumentParser(add_help=False)
    lang.add_argument("--lang", help="comma-separated language codes (default: en)")

    p_tr = sub.add_parser("transcript", parents=[lang], help="fetch clean transcript to a file")
    p_tr.add_argument("url")
    p_tr.add_argument("--refresh", action="store_true", help="ignore cache")
    p_tr.set_defaults(func=_cmd_transcript)

    p_info = sub.add_parser("info", help="video metadata + caption availability")
    p_info.add_argument("url")
    p_info.set_defaults(func=_cmd_info)

    p_search = sub.add_parser("search", parents=[lang], help="find timestamped cues matching a query")
    p_search.add_argument("url")
    p_search.add_argument("query")
    p_search.set_defaults(func=_cmd_search)

    p_seg = sub.add_parser("segment", parents=[lang], help="text within a time range (seconds)")
    p_seg.add_argument("url")
    p_seg.add_argument("start", type=float)
    p_seg.add_argument("end", type=float)
    p_seg.set_defaults(func=_cmd_segment)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
