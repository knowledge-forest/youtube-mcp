# Youtube MCP

> Fast, minimal YouTube "watch" engine for AI agents. Extract clean transcripts, search, and slice any YouTube video — no API key required, no manual setup.

## Install

### Claude Code

```bash
claude mcp add youtube -- uvx --from youtube-mcp yt-mcp serve
```

### Claude Desktop / Codex / other MCP clients

Add to the client's MCP config:

```json
{
  "mcpServers": {
    "youtube": {
      "command": "uvx",
      "args": ["--from", "youtube-mcp", "yt-mcp", "serve"]
    }
  }
}
```

### CLI only

```bash
uvx --from youtube-mcp yt-mcp info "https://youtu.be/VIDEO_ID"
```

That's it. `uvx` pulls `youtube-mcp`, `yt-dlp`, and dependencies into an isolated environment automatically. Nothing to install globally.

> **Optional:** `ffmpeg` on PATH is required **only** for `--asr` (speech-to-text on caption-less videos). Core transcript extraction needs nothing.

## Optional API key

A YouTube Data API key is **not needed** to read videos. Add one only to enable cross-YouTube **search**:

```bash
claude mcp add youtube -e YOUTUBE_API_KEY=your_key -- uvx --from youtube-mcp yt-mcp serve
```

Transcript extraction never uses the key (YouTube only allows caption download for video owners).

## Tools

| Tool | Returns | Purpose |
|------|---------|---------|
| `get_info(url)` | title, duration, chapters, has_captions | Cheap probe before fetching. |
| `get_transcript(url, asr=False)` | file path + word count + preview | Clean transcript to disk. Returns path, not full text. |
| `search_transcript(url, query)` | timestamped snippets | Grep a long video without loading it all. |
| `get_segment(url, start, end)` | text slice | Read one time range. |

Design principle: **pull, don't dump.** Transcripts write to a local cache file; tools return a path and a short preview. The agent reads or searches on demand — long videos never flood the context.


```
/get_info $url
/get_transcript $url
/search_transcript $url
/get_segment $url
```

## Architecture

```
Adapters (thin):   cli.py   mcp_server.py   skill
                        │  call
Core (all logic):  fetch → clean → chunk → cache
                        │  uses
Backends:          youtube-transcript-api · yt-dlp · faster-whisper
```

**Fetch fallback chain:**

1. `youtube-transcript-api` — fastest, no download
2. `yt-dlp` auto-captions
3. `yt-dlp` manual captions
4. `--asr`: audio → local `faster-whisper`

On yt-dlp failure the engine self-updates yt-dlp and retries once — most breakage is a stale yt-dlp.

**Caching:** results are keyed by video ID under `~/.cache/youtube-mcp/<id>/`. Repeat calls are instant.

**Cleaning:** auto-captions are de-duplicated (rolling-caption overlap removed), stripped of timestamps and `[Music]` noise, and whitespace-collapsed before the agent ever sees them.

## Requirements

- Python 3.11+ (managed automatically by `uvx`)
- `ffmpeg` — optional, only for `--asr`

## License

MIT