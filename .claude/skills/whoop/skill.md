---
name: whoop
description: Fetch and analyze Whoop data (recovery, HRV, sleep, strain). Use when the user asks about Whoop data, recovery scores, HRV trends, sleep metrics, or wants to generate a Whoop report.
---

# whoop

Fetch data from the Whoop API and generate analysis reports.

## Fetch latest data (incremental)

```bash
python3 whoop/whoop_fetch.py
```

Downloads only records newer than what's already saved in `whoop-data/`. On first run, triggers a browser OAuth flow (localhost:8080).

## Full re-fetch

```bash
python3 whoop/whoop_fetch.py --full
```

Re-fetches all records from scratch (skips already-saved datasets that haven't changed).

## Generate Excel analysis report

```bash
python3 whoop/whoop_analyze.py
```

Outputs `whoop-data/whoop_metrics.xlsx` with:
- **Daily Metrics sheet** — recovery, HRV RMSSD, 7D/30D rolling HRV-CV, resting HR, sleep stages, strain
- **Summary sheet** — averages across the full date range

## Analysis from a specific date

```bash
python3 whoop/whoop_analyze.py --from 2025-01-01
```

## After fetch

Confirm which files were updated in `whoop-data/` and how many records each has.

## After analyze

Report:
- Output path: `whoop-data/whoop_metrics.xlsx`
- Date range covered
- Avg Recovery Score, Avg HRV RMSSD, Avg Resting HR, Avg Total Sleep

## If credentials are missing

Tell the user to add `WHOOP_CLIENT_ID` and `WHOOP_CLIENT_SECRET` to `.env`. They can create a developer app at https://developer.whoop.com.
