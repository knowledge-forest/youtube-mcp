# TODO

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done

## Milestone 0 — Project setup
- [x] `pyproject.toml`: uv, deps (yt-dlp, youtube-transcript-api), entry point `yt-mcp`
- [x] Package skeleton `src/youtube_mcp/`
- [x] `models.py`: dataclasses — `Info`, `Transcript`, `Segment` (`Hit` deferred to chunk.py)

## Milestone 1 — Core engine (the value)
- [x] `fetch.py`: fallback chain (transcript-api → yt-dlp auto → yt-dlp manual)
- [ ] `fetch.py`: self-heal — update yt-dlp + retry once on failure
- [x] `clean.py`: tier-1 — strip tags/noise markers/entities
- [x] `clean.py`: rolling-caption dedup (biggest token win) — 64% on yt-dlp auto-VTT
- [x] `cache.py`: video-id keyed disk cache (`~/.cache/youtube-mcp/<id>/`)
- [x] `chunk.py`: `search_transcript` (timestamped grep)
- [x] `chunk.py`: `get_segment` (time-range slice)
- [x] `service.py`: orchestration cache→fetch→clean→cache (single entry point)
- [x] `get_info` via yt-dlp (in `fetch.py`); API-key path deferred to search milestone

> **P0 done** (walking skeleton): `info` + `transcript` commands work end-to-end,
> keyless, file-output + preview. Chain verified on transcript-api / yt-dlp manual / yt-dlp auto.

> **P1 done** (the moat): tier-1 clean + rolling dedup (64% reduction on auto-VTT),
> disk cache, `search` + `segment` pull-based tools. Golden dedup tests green (6/6).
> CLI now: `info` / `transcript` / `search` / `segment`.

## Milestone 2 — CLI adapter
- [x] `cli.py`: `info` / `transcript` / `search` / `segment` / `serve`
- [x] File-output + preview behavior (path, not dump)

## Milestone 3 — MCP adapter
- [x] `mcp_server.py`: FastMCP, 4 tools (get_info / get_transcript / search_transcript / get_segment)
- [x] `yt-mcp serve` subcommand (stdio); `noprogress` keeps stdout pure JSON
- [ ] Register `search_videos` only when API key present (deferred — needs the API-key path)
- [ ] Verify stdio transport with a live Claude Code / Desktop client (local install)

> **P2 done**: MCP server exposes 4 pull-based tools over the core engine.
> Verified: tool list, tool execution, pure-JSON stdout (no yt-dlp leak), `♪` stripped.

## Milestone 4 — Distribution
- [ ] Publish to PyPI as `yt-mcp` (server) + `yt-mcp-cli` (CLI) — enables plain `uvx yt-mcp`
- [x] Plugin packaging: `.claude-plugin/plugin.json` (inline MCP server + skills dir)
- [x] `.claude-plugin/marketplace.json` (repo-as-marketplace, source `./`)
- [x] `skills/youtube-watch/SKILL.md` (pull-based workflow + CLI fallback)
- [x] README install commands verified on a live client

> **Name collision fixed**: PyPI `youtube-mcp` is taken (a different RU transcript
> server). Renamed dist to `yt-mcp` (free). Scripts: `yt-mcp` = MCP server,
> `yt-mcp-cli` = CLI. Install = `uvx yt-mcp` (name == package, no flags).

> **P3 done**: plugin + marketplace manifests valid, skill bundled. Install path
> depends on PyPI publish (P4) for `uvx yt-mcp` to resolve.

## Milestone 5 — Tests
- [x] `test_clean.py`: dedup golden tests (critical) — 6
- [x] `test_fetch.py`: id parsing, VTT parse, mocked fallback chain — 11
- [x] `test_cache.py`: store/load round-trip + miss — 3
- [x] `test_chunk.py`: timestamp fmt, search, segment range — 8
- [x] pytest wired (`[dependency-groups] dev`, `uv run pytest`) — 28 passing, network-free
- [ ] E2E test in Claude Code (done ✅), Desktop, Codex

## Milestone 6 — Optional / v2
- [ ] `--asr`: audio download + faster-whisper (caption-less videos)
- [ ] Tier-2 clean: punctuation restoration (local model)
- [ ] `get_playlist(url)` → video ids, loop existing tools
- [ ] Cross-YouTube `search_videos` (API-key gated)
- [ ] Remote HTTP MCP host option
- [ ] `/summarize` add new commands to summarize video
- [ ] Add the commandes


## Non-goals (explicit)
- No channel/creator CRM tools
- No Docker for local use
- No full-transcript dumping into context
- No mandatory API key