# FAQ

Short answers to the questions people actually ask. For internals see
[ARCHITECTURE.md](./ARCHITECTURE.md); for install see the [README](../README.md).

## Setup & install

### Do I need a YouTube / Google API key?

No. Reading a video — info, transcript, search, segment — is fully keyless. The
engine gets captions through `youtube-transcript-api` and `yt-dlp`, neither of
which needs a key.

A YouTube Data API key is **only** for cross-YouTube *search* (finding videos by
keyword), which is a deferred v2 feature. Even then the key is never used for
transcript download — YouTube only allows caption download to the video owner,
so the key would not help.

### Do I need to install yt-dlp / ffmpeg / anything globally?

No. `uvx` pulls `youtube-watch-mcp` and its dependencies (`yt-dlp`,
`youtube-transcript-api`, `mcp`) into a throwaway isolated environment. Nothing
lands on your global Python.

`ffmpeg` is needed **only** for `--asr` (speech-to-text on caption-less videos),
which is a planned v2 feature. Core transcript reading needs nothing extra.

### Why is the install command `uvx youtube-watch-mcp` but the CLI needs `--from`?

Because of how `uvx` resolves names.

| you run | what happens | why |
|---|---|---|
| `uvx youtube-watch-mcp` | starts the MCP server | script name **==** package name, so `uvx` finds it directly |
| `uvx --from youtube-watch-mcp youtube-watch-mcp-cli …` | runs the CLI | script name **≠** package name |

`uvx X` treats `X` as *both* the package to install *and* the command to run.
The CLI script is `youtube-watch-mcp-cli`, which is **not** its own package — it
lives *inside* the `youtube-watch-mcp` package. So you must tell `uvx` which
package to install with `--from`, then which script to run.

### The package is called `youtube-watch-mcp`, not `youtube-mcp` — why?

`youtube-mcp` was already taken on PyPI by an unrelated project. `yt-mcp` was
rejected too (PyPI normalizes it to `ytmcp`, which collides with an existing
`ytmcp`). `youtube-watch-mcp` is distinct and normalizes to `youtubewatchmcp`.
The import path inside the code is still `youtube_mcp`; only the *distribution*
name differs.

## Behavior & limits

### Does it work on videos with no captions?

Not yet. Today the engine reads existing captions (manual or auto-generated). A
video with captions fully disabled returns a "no transcript" error. Speech-to-
text (`--asr`, local `faster-whisper`) is planned for v2 to cover that case.

Use `get_info` first — it reports `has_captions` — so you know before fetching.

### Won't a 2-hour video flood my context?

No — that is the core design choice. Transcripts are **never** dumped into
context. `get_transcript` writes the cleaned transcript to a local file and
returns only a *path*, a short preview, and word count. To read detail you
either open the file yourself or pull just what you need:

- `search_transcript(url, query)` → timestamped snippets of matching moments
- `get_segment(url, start, end)` → one time range

So a long video costs a handful of tokens up front, and you spend more only on
the parts you actually read. This is the "pull, don't dump" principle.

### The raw YouTube auto-caption is a mess (repeated words, `[Music]`, `♪`). Fixed?

Yes, that is the main value-add. Auto-captions scroll: each cue re-shows the tail
of the previous cue plus a few new words. The cleaner keeps only the *new* words
per cue (preserving the correct onset timestamp), strips markup, `[Music]`-style
noise markers, music-note glyphs, and HTML entities, and collapses whitespace.
On real auto-caption VTT this cuts ~64% of the tokens before the agent sees
anything. See [ARCHITECTURE.md → Cleaning](./ARCHITECTURE.md#cleaning-the-moat).

### Which caption source does it use? Can I force a language?

It tries sources fastest-first and returns the first that yields text:

1. `youtube-transcript-api` (no download)
2. `yt-dlp` automatic captions
3. `yt-dlp` manual captions

Pass a language with `lang` (e.g. `lang="en"` or `lang="en,es"` for a preference
order). Default is `en`.

### It fails to fetch — "unable to extract". What now?

Usually a stale `yt-dlp`: YouTube changed its page and your `yt-dlp` predates the
fix. The engine self-heals — on an extraction failure it upgrades `yt-dlp` in
place once and retries. If you invoke through `uvx --refresh`, you already get
the latest `yt-dlp` each run. If it still fails, the video may genuinely have no
captions.

### Where does it cache? How do I clear it?

`~/.cache/youtube-mcp/<video_id>/` (a `segments.json` + `transcript.txt` per
video). Delete that directory to clear. Repeat calls on the same video are
served from cache instantly; pass `refresh=True` (service layer) to re-fetch.

## Usage

### Recommended flow?

1. `get_info(url)` — cheap probe: title, duration, chapters, `has_captions`.
2. Short video → `get_transcript` and read the file.
3. Long video → `search_transcript` to locate moments, then `get_segment` to
   read those ranges.
4. Cite timestamps as `[m:ss]` from the snippet's `timestamp` field.

### Can I use it without Claude Code — plain terminal?

Yes:

```bash
uvx --from youtube-watch-mcp youtube-watch-mcp-cli info "https://youtu.be/VIDEO_ID"
uvx --from youtube-watch-mcp youtube-watch-mcp-cli transcript "URL"
uvx --from youtube-watch-mcp youtube-watch-mcp-cli search "URL" "query"
uvx --from youtube-watch-mcp youtube-watch-mcp-cli segment "URL" 65 200
```

Same core engine as the MCP server — the CLI is just a second thin adapter.
