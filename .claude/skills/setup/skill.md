---
name: setup
description: Set up fitbridge for first use — install dependencies and configure credentials. Use when the user says "setup", "configure", "get started", "install", or opens a fresh clone.
---

# setup

Walk the user through installing dependencies and configuring credentials for all platforms.

## Step 1: Run setup.sh

```bash
bash setup.sh
```

Read the output carefully. If any hard prerequisite is missing (Python, Node.js, pnpm), help the user install it before continuing:
- Python: `brew install python` or https://python.org/downloads
- Node.js: `brew install node` or https://nodejs.org
- pnpm: `npm install -g pnpm`

If the submodule is missing: `git submodule update --init`

Do not continue to credentials until all prerequisites are ✅.

---

## Step 2: Credentials

Read the current `.env` before each section. If all keys for a section are already filled, confirm and skip it.

### COROS

Ask for COROS email and password. Write to `.env`:
```
COROS_EMAIL=<email>
COROS_PASSWORD=<password>
COROS_API_URL=https://api.coros.com
```

### Strava

**If STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET are missing:**
1. Tell the user to go to https://www.strava.com/settings/api and create an app
2. Set "Authorization Callback Domain" to `localhost`
3. Ask them to paste their Client ID and Client Secret, then write to `.env`

**Once client_id and client_secret are set — get tokens:**
```bash
python3 tools/strava_oauth.py
```
This opens a browser, walks through OAuth, and writes STRAVA_ACCESS_TOKEN and STRAVA_REFRESH_TOKEN to `.env` automatically.

### Garmin

Ask for Garmin Connect email and password. Write to `.env`:
```
GARMIN_EMAIL=<email>
GARMIN_PASSWORD=<password>
```

---

### Whoop (optional)

Ask if the user wants Whoop integration. If no, skip.

If yes:
1. Guide to https://developer.whoop.com to create a developer app
2. Ask for Client ID and Client Secret → write to `.env`:
   ```
   WHOOP_CLIENT_ID=<id>
   WHOOP_CLIENT_SECRET=<secret>
   ```
3. Run first fetch (triggers browser OAuth on port 8080):
   ```bash
   python3 whoop/whoop_fetch.py
   ```

---

## Step 3: TrainingPeaks MCP (optional)

Ask the user if they want TrainingPeaks integration. If no, skip this step.

If yes:

**Confirm install path** — suggest `~/Developer/trainingpeaks-mcp` as the default. Accept whatever path the user confirms. Expand `~` to the full absolute path (e.g. `/Users/boriscortes/Developer/trainingpeaks-mcp`) — MCP configs require absolute paths.

```bash
# Clone to confirmed path
git clone https://github.com/JamsusMaximus/trainingpeaks-mcp <absolute_path>
cd <absolute_path> && pip install -e .

# Authenticate via Chrome
tp-mcp auth --from-browser chrome
```

After auth completes, write two things:

**a) `.env`** — using the absolute path:
```
TP_MCP_PATH=<absolute_path>
```

**b) `.claude/settings.local.json`** — MCP server config (detect python3 path first):
```bash
which python3
```

Then write `.claude/settings.local.json`:
```json
{
  "mcpServers": {
    "trainingpeaks": {
      "command": "<python3_path>",
      "args": ["-m", "tp_mcp"],
      "cwd": "<absolute_path>"
    }
  }
}
```

Tell the user to **restart Claude Code** after this step for the MCP server to load.

---

## Step 4: Validate

```bash
python3 coros_sync.py --help
```

If this prints the help text, setup is complete.

---

## Final message

Summarize what was configured:
- ✅ / ⏭️ (skipped) for each section: COROS, Strava, Garmin, TrainingPeaks
- Remind them to restart Claude Code if the TP MCP server was configured
- Tell them they're ready to use `/sync`, `/route`, and `/whoop`
