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

## Routes

Base GPX loops live in `routes/base/`. Generated routes go to `routes/out/` (gitignored). To add a new base loop, drop a `.gpx` file into `routes/base/`.
