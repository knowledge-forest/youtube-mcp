# Architecture

How the pieces fit and *why*. For usage see the [README](../README.md); for
common questions see [FAQ.md](./FAQ.md).

## One idea

**One core engine, thin adapters, pull-based output.** All logic lives in the
core; each interface (CLI, MCP server, plugin skill) is a small adapter that
calls the same functions. Nothing dumps a full transcript into an agent's
context — tools return paths, previews, and timestamped snippets.

## Layers

```
Adapters (thin):   cli.py        mcp_server.py     skills/youtube-watch
                        │              │  MCP tools       │ prompt
                        └──────────────┴──────────────────┘
                                       │ call
Core (all logic):   service.py  ──▶  fetch ─▶ clean ─▶ cache
                                       │        ▲
                                   chunk.py ────┘  (search / segment read cache)
                                       │
Backends:           youtube-transcript-api   ·   yt-dlp
```

- **Adapters never contain business logic.** `mcp_server.py` maps 4 MCP tools to
  core functions and shapes the return dict. `cli.py` maps subcommands the same
  way. Swapping or adding an interface touches no core code.
- **`service.get_transcript` is the single entry point** for a cleaned,
  cached transcript. Every adapter and `chunk.py` goes through it, so cleaning
  and caching happen exactly once, in one place.

## Modules (`src/youtube_mcp/`)

| module | role | key symbols |
|---|---|---|
| `models.py` | plain dataclasses, no logic | `Info`, `Transcript` (`.text`, `.word_count`), `Segment`, `Hit` |
| `fetch.py` | get raw captions + video info; fallback chain; self-heal | `fetch_transcript`, `get_info`, `extract_video_id`, `_ytdlp_call` |
| `clean.py` | tier-1 clean + rolling-caption dedup (the moat) | `clean_text`, `_new_words`, `dedup_segments` |
| `cache.py` | video-id-keyed disk cache | `load`, `store`, `transcript_path` |
| `service.py` | orchestrate cache → fetch → clean → cache | `get_transcript` |
| `chunk.py` | read helpers over a transcript | `search_transcript`, `get_segment`, `format_timestamp` |
| `cli.py` | human CLI adapter | `main` |
| `mcp_server.py` | MCP adapter (FastMCP, 4 tools) | `serve` |

## Data flow

`get_transcript(url)`:

```
url ─▶ extract_video_id
        │
        ▼
   cache.load(id)? ──yes──▶ return cached Transcript   (instant)
        │ no
        ▼
   fetch_transcript ─▶ clean_transcript ─▶ cache.store ─▶ return
```

`search_transcript` / `get_segment` call `get_transcript` (so they hit the same
cache), then filter/slice its segments — they never re-fetch on their own.

## Fetch fallback chain

Tried fastest-first; first source that yields non-empty text wins
(`fetch.py::fetch_transcript`):

1. **`youtube-transcript-api`** — no media download, just the caption endpoint.
   Fastest. Supports both the 1.x instance API (`fetch`) and 0.6.x classmethod
   API (`get_transcript`).
2. **`yt-dlp` automatic captions** — downloads the auto-generated VTT track.
3. **`yt-dlp` manual captions** — downloads the human/manual VTT track.

Each source's exception is collected and the chain continues; if all fail,
`FetchError` is raised with every source's message.

### Self-heal

yt-dlp breaks when YouTube changes its page layout; a newer yt-dlp usually
already carries the fix. `_ytdlp_call` wraps every yt-dlp operation
(`_ytdlp_subs`, `get_info`): on a `DownloadError` it calls `_heal_ytdlp()` —
`pip install --upgrade yt-dlp` then `importlib.reload` — and retries the call
**once**. A process-wide flag (`_healed_once`) ensures the upgrade is attempted
at most once per process, so repeated failures don't trigger an upgrade storm.
If the upgrade can't run (read-only env, no network), the original error
surfaces cleanly. The `youtube-transcript-api` path is unaffected.

## Cleaning (the moat)

`clean.py` is the main value-add. Raw YouTube auto-captions are a scrolling
window: each cue re-shows the tail of the previous cue plus a few new words, so a
naive join repeats almost everything.

- **`clean_text`** strips HTML tags, unescapes entities, removes `[...]` noise
  markers (`[Music]`, `[Applause]`), music-note glyphs (`♪♫…`), and collapses
  whitespace.
- **`_new_words(prev, cur)`** finds the largest overlap `k` where `prev`'s last
  `k` words equal `cur`'s first `k` words, then drops those `k` words — keeping
  only what's genuinely new in each cue.
- **`dedup_segments`** applies both while **preserving each cue's onset
  timestamp**, so `search`/`segment` stay time-accurate after collapse.

Net effect: ~64% fewer tokens on real auto-caption VTT before the agent sees
anything. Golden tests live in `tests/test_clean.py`.

## Cache

`cache.py` — keyed by video id under `~/.cache/youtube-mcp/<id>/`:

- `segments.json` — cleaned segments (source, language, per-cue text + timing);
  the source of truth reloaded by `cache.load`.
- `transcript.txt` — the flat cleaned prose (what `get_transcript`'s `path`
  points at for a human/agent to read).

Repeat calls on a video are served from disk instantly. `service.get_transcript`
takes `refresh=True` to bypass and re-fetch.

## Adapters

### MCP server (`mcp_server.py`)

FastMCP app named `youtube`, stdio transport (`serve()` → `mcp.run()`). Four
pull-based tools:

| tool | returns |
|---|---|
| `get_info(url)` | title, duration, chapters, `has_captions` |
| `get_transcript(url, lang?)` | `path` + preview (first 200 words) + `word_count` + source/lang — **not** full text |
| `search_transcript(url, query, lang?)` | list of `{timestamp, start_seconds, text}` |
| `get_segment(url, start, end, lang?)` | text for the half-open range `[start, end)` |

stdout must stay pure JSON-RPC, so yt-dlp is run with `quiet`, `no_warnings`,
`noprogress` — no progress bars leak into the transport.

### CLI (`cli.py`)

`argparse` with subcommands `info` / `transcript` / `search` / `segment` /
`serve` (`serve` lazily imports `mcp_server`). Same core calls as the MCP tools.

### Plugin skill (`skills/youtube-watch/SKILL.md`)

Teaches the get-info-first workflow, short-vs-long strategy, CLI fallback, and
`[m:ss]` citation. Pure prompt — no code.

## Versioning & distribution

- Version is **not** stored in any file — `hatch-vcs` derives it from the latest
  git tag at build time and writes `src/youtube_mcp/_version.py` (gitignored).
  Runtime reads it via `importlib.metadata.version("youtube-watch-mcp")`.
- Plugin/marketplace JSONs carry **no** version field for the same reason.
- Published to PyPI as `youtube-watch-mcp`; two console scripts:
  `youtube-watch-mcp` (server) and `youtube-watch-mcp-cli` (CLI).
- `scripts/release.sh` is the tag → push → build → publish path.

## Design boundaries (non-goals)

- No full-transcript dumping into context — always pull-based.
- No mandatory API key.
- No Docker for local use — `uvx` only.
- No channel/creator CRM tooling.

## Planned (v2)

`--asr` (audio → local `faster-whisper`) for caption-less videos, tier-2
punctuation restoration, `get_playlist`, API-key-gated cross-YouTube
`search_videos`, remote HTTP MCP host. Tracked in [TODO.md](../TODO.md).
