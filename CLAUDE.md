# fitbridge

This workspace syncs fitness activities from COROS to Strava, Garmin Connect, and TrainingPeaks, and generates exact-distance GPS routes from base loops.

## Credentials

All credentials live in `.env` (copy from `.env.example`):
- `COROS_EMAIL` / `COROS_PASSWORD` / `COROS_API_URL` — COROS account
- `STRAVA_CLIENT_ID` / `STRAVA_CLIENT_SECRET` / `STRAVA_ACCESS_TOKEN` / `STRAVA_REFRESH_TOKEN` — Strava API app
- `GARMIN_EMAIL` / `GARMIN_PASSWORD` — Garmin Connect account
- `TP_MCP_PATH` (optional) — path to a local trainingpeaks-mcp install (e.g. `~/Developer/trainingpeaks-mcp`); run `tp-mcp auth` once to store the session cookie

## Scripts

- `coros_sync.py` — downloads new FIT files from COROS and uploads to Strava, Garmin, and/or TrainingPeaks
- `strava_refresh.py` — Strava OAuth token refresh helper
- `tools/tile_route.py` — tiles a base GPX loop to an exact target distance

## Skills

Use `/sync` to sync activities and `/route` to generate routes. Both can also be triggered by natural language.

## Key behaviors

- Walks are skipped by default during batch sync; use `--walks` or `--file` to include them
- COROS always exports all sport types (including walks) to `coros-exports/`; walk filtering happens at upload time
- `--file PATH` bypasses the walk filter and COROS download — use for one-off uploads
- Strava deduplicates by start time (±60s); Garmin handles 409 duplicates automatically
- Logs written to `logs/coros_sync.log` (rotating, 1 MB cap)
- TrainingPeaks upload is a two-step operation: creates a blank workout, then attaches the FIT file

## Whoop

Scripts live in `whoop/`. Data is fetched to `whoop-data/` (gitignored).

- `whoop/whoop_fetch.py` — fetch latest data from Whoop API (incremental by default); triggers browser OAuth on first run (port 8080)
- `whoop/whoop_analyze.py` — generate `whoop-data/whoop_metrics.xlsx` with HRV trends, recovery scores, sleep stages, rolling HRV-CV
- Auth tokens stored in `whoop-data/whoop_tokens.json`

Requires `WHOOP_CLIENT_ID` and `WHOOP_CLIENT_SECRET` in `.env`. Create a developer app at https://developer.whoop.com.
Use `/whoop` skill to fetch and analyze data.

## Routes

Base GPX loops live in `routes/base/`. Generated routes go to `routes/out/` (gitignored). To add a new base loop, drop a `.gpx` file into `routes/base/`.
