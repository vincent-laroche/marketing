# Instagram Saves Content Engine

> **Moved:** this tool was moved from [`vincent-laroche/instagram-saves-content-engine`](https://github.com/vincent-laroche/instagram-saves-content-engine) into `tools/instagram-saves/` on 2026-10-04. The Notion databases `Instagram Saves` and `Content Ideas`, plus the twice-daily launchd job, remain the system of record. The old repository will be archived after a successful local verify from this path.

Local-first pipeline for Hair Solutions Co. that syncs saved Instagram posts into Notion and turns unprocessed saves into reviewed content ideas.

## What It Does

1. Reads saved Instagram posts with your browser session cookies.
2. Writes new saves once into a Notion database named `Instagram Saves`.
3. Tracks duplicates by Media ID and Shortcode in `data/sync_state.json`.
4. Lets you manually review New saves and generate conservative Hair Solutions Co. content ideas.
5. Writes only approved ideas into a Notion database named `Content Ideas`.
6. Marks source saves as `Processed` or `Reviewed`.
7. Runs sync twice daily on macOS with launchd.

No public server is required. Instagram behavior is read-only.

## Architecture

- `instagram_client.py`: read-only saved-post fetch using local browser-session cookies.
- `notion_client.py`: Notion validation, page creation, status updates, and property mapping.
- `state.py`: local JSON state for duplicate prevention.
- `sync.py`: Instagram to Notion sync orchestration.
- `ideate.py`: OpenAI-assisted content idea generation with safety guardrails.
- `cli.py`: `instagram-saves` commands.

## Setup

```bash
cd /Users/vincent/<marketing checkout>/tools/instagram-saves
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Fill `.env` with Notion token, database IDs, Instagram cookies, and optionally `OPENAI_API_KEY`.

For Reel audio enrichment, install the optional local transcription dependency:

```bash
pip install -e ".[enrichment]"
```

The enrichment command also expects `/Users/vincent/02_dev/content-factory` to exist (it is a separate local checkout and must be present; override with `CONTENT_FACTORY_PATH` in `.env`) with its Node dependencies installed, plus local `ffmpeg` and `yt-dlp`.

## Commands

```bash
instagram-saves validate-config
instagram-saves validate-notion
instagram-saves sync
instagram-saves enrich-reels
instagram-saves list-new
instagram-saves ideate
instagram-saves mark-reviewed
instagram-saves show-state
```

Equivalent module form:

```bash
python -m instagram_saves_engine sync
```

## Manual Sync

```bash
instagram-saves sync
```

The summary reports fetched, created, duplicate-skipped, updated, and error counts.

## Manual Ideation

```bash
instagram-saves ideate
```

The command lists New saves, asks what to process, generates structured ideas, then asks before writing anything to Notion.

## Reel Enrichment

```bash
instagram-saves enrich-reels --limit 3
```

This command reuses the local `content-factory` reel transcription engine to extract audio transcripts for synced Instagram Reels, then writes `Audio Transcript`, `Combined Script`, and transcription status back to the `Instagram Saves` database. Use a small limit first because reel transcription downloads audio and can take several minutes per batch.

The command is separate from scheduled sync on purpose: syncing saved items stays fast and reliable, while video/audio extraction remains an on-demand enrichment step.

## Scheduler

Install twice-daily sync at 9:00 AM and 9:00 PM:

```bash
chmod +x scripts/*.sh
scripts/install_launchd.sh
```

Verify:

```bash
launchctl list | grep hairsolutions.instagram-saves-sync
```

Uninstall:

```bash
scripts/uninstall_launchd.sh
```

## Security Notes

- `.env`, `data/`, and `logs/` are ignored by git.
- Cookies, tokens, keys, and database IDs are never printed intentionally.
- Raw Instagram debug JSON is sanitized and truncated before storage.
- The Instagram client does not post, delete, DM, comment, like, follow, or modify content.
- If Instagram blocks, challenges, or rate-limits the request, the sync stops.

## Limitations

- Instagram does not provide a stable public saved-post API for this use case. The browser-session endpoint may change.
- Cookie-based sync requires replacing expired cookies.
- Notion database property names must match the docs.
- OpenAI is required only for `ideate`; sync works without it.
- Visual OCR from reel screenshots is not part of unattended sync yet. The merged enrichment path currently adds audio transcription and preserves fields for OCR/on-screen text.

See `docs/` for setup and troubleshooting details.
