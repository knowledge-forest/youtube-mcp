# TODO

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done

## Milestone 0 — Project setup
- [x] `pyproject.toml`: uv, deps (yt-dlp, youtube-transcript-api), entry point `yt-core`
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
- [ ] `cli.py`: `info` / `transcript` / `search` / `segment`
- [ ] File-output + preview behavior (path, not dump)

## Milestone 3 — MCP adapter
- [ ] `mcp_server.py`: FastMCP, 4 tools
- [ ] Register `search`-family tools only when API key present
- [ ] Verify stdio transport with Claude Code

## Milestone 4 — Distribution
- [ ] Publish to PyPI as `yt-core` (enables `uvx`)
- [ ] Plugin packaging: `.claude-plugin/plugin.json` (MCP + skill together)
- [ ] `skill/SKILL.md` for Claude Code (run CLI + native Read/Grep)
- [ ] README install commands verified on each client

## Milestone 5 — Tests
- [ ] `test_clean.py`: dedup golden tests (critical)
- [ ] `test_fetch.py`: mocked fallback chain
- [ ] `test_cache.py`: hit/miss behavior

## Milestone 6 — Optional / v2
- [ ] `--asr`: audio download + faster-whisper (caption-less videos)
- [ ] Tier-2 clean: punctuation restoration (local model)
- [ ] `get_playlist(url)` → video ids, loop existing tools
- [ ] Cross-YouTube `search_videos` (API-key gated)
- [ ] Remote HTTP MCP host option

## Non-goals (explicit)
- No channel/creator CRM tools
- No Docker for local use
- No full-transcript dumping into context
- No mandatory API key