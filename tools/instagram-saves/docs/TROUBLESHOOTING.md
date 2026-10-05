# Troubleshooting

## Notion Token Invalid

Run `instagram-saves validate-notion`. If it fails, update `NOTION_TOKEN` in `.env`.

## Database Not Shared

Share both databases with the Notion integration. Then rerun `instagram-saves validate-notion`.

## Missing Notion Properties

Property names must match exactly. See `docs/NOTION_SETUP.md`.

## Instagram Cookies Expired

Replace the Instagram cookie values in `.env`, then run:

```bash
instagram-saves sync
```

## Instagram Request Blocked

The script stops on block, challenge, or rate limit. Open Instagram in the browser and resolve any account review manually.

## Duplicate Entries

The system checks local state and Notion by Media ID and Shortcode. If duplicates were manually created, merge or archive them in Notion, then keep the state file.

## Launchd Did Not Run

Check:

```bash
launchctl list | grep hairsolutions.instagram-saves-sync
cat logs/launchd.err.log
```

Confirm `.venv` exists and dependencies are installed.

## OpenAI Key Missing

Sync still works. `instagram-saves ideate` requires `OPENAI_API_KEY`.

## Long Captions Truncated

Notion rich text fields have practical limits. Long captions and raw JSON are truncated with a note.

## Reel Enrichment Fails

Run `instagram-saves enrich-reels --limit 1` first. Common causes:

- `mlx_whisper` is missing: install with `pip install -e ".[enrichment]"`.
- `ffmpeg` or `yt-dlp` is missing locally.
- `/Users/vincent/02_dev/content-factory` is missing or its `node_modules` folder is not installed.
- Instagram cookies expired or no longer allow media download.
- The first local Whisper run may need time to download the model before transcription starts.

The command writes a short failure reason to `Extraction Notes` on the Notion save.
