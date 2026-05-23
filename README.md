# fitbridge

Sync fitness activities from COROS to **Strava**, **Garmin Connect**, and **TrainingPeaks** in one command. Fetch and analyze **Whoop** recovery data. Generate exact-distance GPX routes from a base loop.

## Features

- Downloads new FIT files from COROS (skips already-synced files)
- Deduplicates against existing Strava activities (±60 second tolerance)
- Handles Garmin Connect 409 duplicates gracefully, with automatic retry on network errors
- Uploads to any combination of Strava, Garmin, and TrainingPeaks
- Skips walks by default; include them with `--walks` or sync a single file with `--file`
- Fetches Whoop recovery, HRV, sleep, and strain data; exports to Excel with rolling metrics
- Uses your system timezone automatically (no hardcoded offsets)
- Rotating file logs at `logs/coros_sync.log`

## Usage with Claude Code

Clone the repo and open it in Claude Code:

```bash
git clone --recurse-submodules https://github.com/boriscortes/fitbridge.git
cd fitbridge
claude   # opens Claude Code in this workspace
```

New here? Type `/setup` to be guided through credentials and dependencies.

Then ask naturally:
- "Sync today's activities"
- "Sync last 7 days to Strava only"
- "Upload this FIT file to Garmin"
- "Generate a 26km route from central park"
- "Fetch my latest Whoop data and generate a report"

Available skills: `/setup`, `/sync`, `/route`, `/whoop`

---

## CLI usage (advanced)

### Prerequisites

- Python 3.9+
- Node.js + pnpm (for the COROS API wrapper)
- Python packages: `python3 -m pip install fitparse garminconnect requests openpyxl`
- TrainingPeaks (optional): [trainingpeaks-mcp](https://github.com/JamsusMaximus/trainingpeaks-mcp) installed and authed
- Whoop (optional): developer app credentials from https://developer.whoop.com

### Setup

```bash
git clone --recurse-submodules https://github.com/boriscortes/fitbridge.git
cd fitbridge

# Automated setup (installs deps, checks credentials)
bash setup.sh

# Or manually:
python3 -m pip install fitparse garminconnect requests openpyxl
cd coros-api && pnpm install && cd ..

cp .env.example .env
# Edit .env with your credentials
```

### Strava credentials

1. Create an app at https://www.strava.com/settings/api
2. Set `Authorization Callback Domain` to `localhost`
3. Run the OAuth helper to get your tokens automatically:

```bash
python3 tools/strava_oauth.py
```

### TrainingPeaks (optional)

```bash
# Clone to a path of your choice
git clone https://github.com/JamsusMaximus/trainingpeaks-mcp ~/Developer/trainingpeaks-mcp
cd ~/Developer/trainingpeaks-mcp && pip install -e .

# Authenticate via Chrome (stores session cookie in system keyring)
tp-mcp auth --from-browser chrome

# Add to .env:
# TP_MCP_PATH=~/Developer/trainingpeaks-mcp
```

### Whoop (optional)

1. Create a developer app at https://developer.whoop.com
2. Add to `.env`:
   ```
   WHOOP_CLIENT_ID=your_client_id
   WHOOP_CLIENT_SECRET=your_client_secret
   ```
3. Run the first fetch — this opens a browser OAuth flow on port 8080:
   ```bash
   python3 whoop/whoop_fetch.py
   ```

## Activity sync

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

## Whoop data

```bash
# Fetch latest data (incremental)
python3 whoop/whoop_fetch.py

# Full re-fetch from scratch
python3 whoop/whoop_fetch.py --full

# Generate Excel report (recovery, HRV, sleep, strain)
python3 whoop/whoop_analyze.py

# Analyze from a specific date
python3 whoop/whoop_analyze.py --from 2025-01-01
```

Output: `whoop-data/whoop_metrics.xlsx` with daily metrics and rolling HRV-CV trends.

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
├── CLAUDE.md           # Claude Code workspace guide
├── coros_sync.py       # main sync script
├── strava_refresh.py   # Strava OAuth helper
├── coros-api/          # COROS API wrapper (git submodule)
├── tools/
│   ├── tile_route.py   # GPX route tiler
│   └── strava_oauth.py # Strava OAuth token helper
├── whoop/
│   ├── whoop_auth.py   # Whoop OAuth token management
│   ├── whoop_fetch.py  # fetch data from Whoop API
│   └── whoop_analyze.py # generate Excel report
├── routes/
│   ├── base/           # source GPX loops
│   └── out/            # generated routes (gitignored)
├── whoop-data/         # fetched Whoop JSON + reports (gitignored)
├── logs/               # rotating sync logs (gitignored)
└── .claude/
    ├── settings.json   # Bash permissions
    └── skills/         # /setup, /sync, /route, /whoop slash commands
```

## Platform notes

| Platform | Auth | Notes |
|----------|------|-------|
| Strava | OAuth tokens in `.env` | Auto-refreshes on expiry; run `tools/strava_oauth.py` to set up |
| Garmin Connect | Email/password in `.env` | Retries on network error; 409 = duplicate |
| TrainingPeaks | Session cookie via `tp-mcp auth` | Creates blank workout then attaches FIT |
| COROS | Email/password in `.env` | Uses unofficial API — may break on COROS app updates |
| Whoop | OAuth via browser (port 8080) | Tokens stored in `whoop-data/whoop_tokens.json` |
