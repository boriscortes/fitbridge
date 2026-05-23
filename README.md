# fitbridge

Sync fitness activities from COROS to **Strava**, **Garmin Connect**, and **TrainingPeaks** in one command. Also includes a GPX route tiling tool for generating exact-distance training routes from a base loop.

## Features

- Downloads new FIT files from COROS (skips already-synced files)
- Deduplicates against existing Strava activities (±60 second tolerance)
- Handles Garmin Connect 409 duplicates gracefully, with automatic retry on network errors
- Uploads to any combination of Strava, Garmin, and TrainingPeaks
- Skips walks by default; include them with `--walks` or sync a single file with `--file`
- Uses your system timezone automatically (no hardcoded offsets)
- Rotating file logs at `logs/coros_sync.log`

## Prerequisites

- Python 3.9+
- Node.js + pnpm (for the COROS API wrapper)
- Python packages: `pip install fitparse garmin-connect requests`
- TrainingPeaks (optional): [trainingpeaks-mcp](https://github.com/your-org/trainingpeaks-mcp) installed and authed

## Setup

```bash
git clone --recurse-submodules https://github.com/boriscortes/fitbridge.git
cd fitbridge

# Install Python dependencies
pip install fitparse garmin-connect requests

# Install COROS API wrapper
cd coros-api && pnpm install && cd ..

# Configure credentials
cp .env.example .env
# Edit .env with your Strava, Garmin, and COROS credentials
```

### Strava credentials

1. Create an app at https://www.strava.com/settings/api
2. Set `Authorization Callback Domain` to `localhost`
3. Run the OAuth flow once to get your `access_token` and `refresh_token`

### TrainingPeaks (optional)

```bash
# Install trainingpeaks-mcp
git clone https://github.com/your-org/trainingpeaks-mcp ~/Developer/trainingpeaks-mcp
cd ~/Developer/trainingpeaks-mcp && pip install -e .

# Authenticate (stores session cookie in system keyring)
tp-mcp auth

# Add to .env:
# TP_MCP_PATH=~/Developer/trainingpeaks-mcp
```

## Usage

```bash
# Sync today's activities to all configured platforms
python3 coros_sync.py

# Sync last 7 days
python3 coros_sync.py --days 7

# Strava only
python3 coros_sync.py --strava

# Garmin only
python3 coros_sync.py --garmin

# TrainingPeaks only
python3 coros_sync.py --tp

# Include walks (skipped by default)
python3 coros_sync.py --walks

# Upload a specific FIT file directly (bypasses walk filter)
python3 coros_sync.py --file path/to/activity.fit

# Reprocess all files in date range (including already-downloaded)
python3 coros_sync.py --days 7 --force
```

## Route generation

Generate an exact-distance GPX route by tiling a base loop. Useful for loading into COROS or Garmin as a course for treadmill grade simulation or paced runs.

```bash
# Generate a 26 km route from the Central Park loop
python3 tools/tile_route.py central_park_loop 26

# Custom output directory
python3 tools/tile_route.py central_park_loop 16 --routes-base routes/base --routes-out routes/out
```

Add your own base loops to `routes/base/` as `.gpx` files.

## Project structure

```
fitbridge/
├── coros_sync.py       # main sync script
├── strava_refresh.py   # Strava OAuth helper
├── coros-api/          # COROS API wrapper (git submodule)
├── tools/
│   └── tile_route.py   # GPX route tiler
├── routes/
│   ├── base/           # source GPX loops
│   └── out/            # generated routes (gitignored)
├── analysis/           # data analysis scripts (WIP)
└── logs/               # rotating sync logs (gitignored)
```

## Platform notes

| Platform | Auth | Notes |
|----------|------|-------|
| Strava | OAuth tokens in `.env` | Auto-refreshes on expiry |
| Garmin Connect | Email/password in `.env` | Retries on network error; 409 = duplicate |
| TrainingPeaks | Session cookie via `tp-mcp auth` | Creates blank workout then attaches FIT |
| COROS | Email/password in `.env` | Uses unofficial API — may break on COROS app updates |
