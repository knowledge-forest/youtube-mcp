---
name: youtube-watch
description: Watch/read a YouTube video — pull its transcript, search it, or read a time range. Use when the user shares a YouTube URL and wants its content summarized, quoted, searched, or analyzed. Backed by the yt-mcp server (tools get_info / get_transcript / search_transcript / get_segment); falls back to the yt-mcp-cli command.
---

# Watching a YouTube video

Goal: get a video's content into context **efficiently** — never dump a whole
transcript when a search or a slice will do. Long videos otherwise blow the
token budget.

## Decide the approach with `get_info` first

Call `get_info(url)` (MCP) or `yt-mcp-cli info URL`. It returns title, duration,
chapters, and `has_captions` — cheap, no transcript. Use it to choose:

- **Short video (< ~10 min)** → `get_transcript`, then read the whole file.
- **Long video** → `get_transcript` for the path + preview, then **`search_transcript`**
  or **`get_segment`** to pull only what's relevant. Do not read the full file.
- **No captions** (`has_captions: false`) → transcript needs ASR (`--asr`, slower,
  opt-in); warn the user before doing it.

## Tools (MCP server `yt-mcp`)

| Tool | When |
|------|------|
| `get_info(url)` | Always first. Metadata + caption availability. |
| `get_transcript(url, lang?)` | Get the cleaned transcript. Returns a **file path + preview**, not the full text. |
| `search_transcript(url, query)` | Find where something is said. Returns timestamped snippets. |
| `get_segment(url, start, end)` | Read one time range (seconds). |

`get_transcript` writes the cleaned transcript to a cache file and returns its
path. For a short video, read that file. For a long one, prefer search/segment.

## Reading the transcript file

The path from `get_transcript` points at cleaned prose in
`~/.cache/youtube-mcp/<video_id>/transcript.txt`. Read it with the normal Read
tool, or grep it — it's already de-duplicated and stripped of markup/noise.

## CLI fallback (no MCP server)

If the MCP server isn't connected, use the command directly:

```bash
yt-mcp-cli info    "URL"
yt-mcp-cli transcript "URL"          # -> prints cache path + preview
yt-mcp-cli search  "URL" "query"     # -> [m:ss] snippet
yt-mcp-cli segment "URL" 120 180     # -> text in [120s, 180s)
```

## Answering the user

- Cite timestamps (`[m:ss]`) when quoting, so the user can jump to the moment.
- For "summarize this video": short → read full transcript; long → skim chapters
  via `get_info`, then `get_segment` per chapter, summarize each.
- Never claim to have "watched" visuals — this reads captions/audio, not frames.
