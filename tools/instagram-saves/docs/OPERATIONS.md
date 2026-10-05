# Operations

## Daily Use

Let launchd run sync at 9:00 AM and 9:00 PM. When you want to turn saves into content ideas:

```bash
instagram-saves list-new
instagram-saves ideate
```

Review every generated idea before approval. Approved ideas are written to Notion and the source save is marked `Processed`.

## Manual Sync

```bash
instagram-saves sync
```

Run one successful manual sync before installing launchd. The installer now refuses to install if the required Instagram cookie values are missing from the project `.env`.

## Reel Enrichment

Run this manually after sync when you want the system to inspect what is said inside saved Reels:

```bash
instagram-saves enrich-reels --limit 3
```

Start with a small limit. The command uses the local `content-factory` transcriber bridge, writes transcript artifacts under `data/reel_enrichment`, and updates the same `Instagram Saves` Notion rows with transcript and combined-script fields.

Requirements for this command:

- `/Users/vincent/02_dev/content-factory` exists (separate local checkout; override with `CONTENT_FACTORY_PATH`) and has `node_modules` installed.
- `ffmpeg` and `yt-dlp` are available locally.
- The Python optional dependency is installed with `pip install -e ".[enrichment]"`.
- Instagram cookies in `.env` are still valid, because `yt-dlp` uses them to read saved Reel media.

## Logs

- launchd stdout: `logs/launchd.out.log`
- launchd stderr: `logs/launchd.err.log`
- command output: terminal

## State File

Default path:

```text
data/sync_state.json
```

It tracks seen Media IDs and Shortcodes. Back it up with the repo if duplicate protection matters across machines.

## Backup

Back up:

- `.env` through your private local backup process
- `data/sync_state.json`
- the two Notion databases

Do not put `.env` into git.

## Token Rotation

1. Create or rotate the token in the provider.
2. Update `.env`.
3. Run `instagram-saves validate-config`.
4. Run `instagram-saves validate-notion` for Notion changes.

## Failed Sync Recovery

1. Read the terminal or launchd error log.
2. Run `instagram-saves validate-config`.
3. Run `instagram-saves validate-notion`.
4. If Instagram cookies expired, replace them.
5. Run `instagram-saves sync` manually.

## Scheduling Alternatives

- `launchd`: default macOS path in this repo.
- `cron`: call `scripts/run_sync.sh` at desired times.
- Manual Codex run: ask Codex to run `instagram-saves sync`.
- GitHub Actions: possible later, but requires storing secrets in GitHub and may be less suitable for Instagram session cookies.
- Future cloud runner: possible later if you decide to host, but not required.
