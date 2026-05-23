---
name: sync
description: Sync COROS activities to Strava, Garmin Connect, and/or TrainingPeaks. Use when the user wants to sync, upload, push, or transfer activities — e.g. "sync today", "push last 7 days to Garmin", "upload this FIT file to Strava", "sync my run from this morning".
---

# sync

Download new COROS activities and upload to fitness platforms.

## How to run

Determine scope and platforms from the user's request, then run from the repo root:

```bash
python3 coros_sync.py [--days N] [--strava] [--garmin] [--tp] [--walks] [--file PATH] [--force]
```

**Scope flags:**
- No flag → today only
- `--days N` → last N days
- `--file PATH` → upload a specific FIT file directly (bypasses walk filter and COROS download)
- `--force` → reprocess all files in the date range (including already-downloaded)

**Platform flags (default: all configured platforms):**
- `--strava` → Strava only
- `--garmin` → Garmin Connect only
- `--tp` → TrainingPeaks only (requires `TP_MCP_PATH` in `.env`)

**Other:**
- `--walks` → include walks (skipped by default)

## Examples

| User says | Command |
|-----------|---------|
| "sync today" | `python3 coros_sync.py` |
| "sync last 7 days" | `python3 coros_sync.py --days 7` |
| "sync last week to Strava only" | `python3 coros_sync.py --days 7 --strava` |
| "upload this file to Garmin" | `python3 coros_sync.py --file path.fit --garmin` |
| "sync including walks" | `python3 coros_sync.py --walks` |
| "reprocess last 3 days" | `python3 coros_sync.py --days 3 --force` |

## After running

Summarize results: how many files were uploaded, any duplicates skipped, any errors. If TrainingPeaks upload fails with an auth error, remind the user to run `tp-mcp auth`.
