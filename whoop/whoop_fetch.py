"""
WHOOP Data Fetcher
Fetches all available data from the WHOOP API and saves to whoop-data/.

Usage:
  python3 whoop/whoop_fetch.py        # incremental: only fetch records newer than saved
  python3 whoop/whoop_fetch.py --full # full re-fetch (skips already-saved datasets)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# Allow running as a script from repo root
sys.path.insert(0, str(Path(__file__).parent))
from whoop_auth import get_valid_tokens

API_BASE   = "https://api.prod.whoop.com/developer/v2"
OUTPUT_DIR = Path(__file__).parent.parent / "whoop-data"


# ── API client ────────────────────────────────────────────────────────────────
def make_session(access_token: str) -> requests.Session:
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {access_token}"
    return s


def paginate(session: requests.Session, endpoint: str, params: dict = None) -> list:
    """Fetch all pages from a paginated WHOOP endpoint, respecting rate limits."""
    params = params or {}
    params["limit"] = 25
    results = []
    request_count = 0

    while True:
        if request_count > 0 and request_count % 50 == 0:
            print(f"\n  Rate limit pause (60s)...", end="\r")
            time.sleep(62)

        resp = session.get(f"{API_BASE}{endpoint}", params=params)

        if resp.status_code == 429:
            print(f"\n  429 rate limited — waiting 65s...", end="\r")
            time.sleep(65)
            continue

        resp.raise_for_status()
        body = resp.json()
        request_count += 1

        records = body.get("records", [])
        results.extend(records)
        print(f"  {endpoint}: fetched {len(results)} records so far...", end="\r")

        next_token = body.get("next_token")
        if not next_token:
            break
        params["nextToken"] = next_token

    print(f"  {endpoint}: {len(results)} total records fetched.       ")
    return results


def fetch_single(session: requests.Session, endpoint: str) -> dict:
    resp = session.get(f"{API_BASE}{endpoint}")
    resp.raise_for_status()
    return resp.json()


# ── Save/load helpers ─────────────────────────────────────────────────────────
def save(name: str, data):
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved → {path}")


def load_saved(name: str):
    path = OUTPUT_DIR / f"{name}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def latest_start(records: list) -> str | None:
    for record in records:
        ts = record.get("start") or record.get("created_at")
        if ts:
            return ts
    return None


# ── Incremental update ────────────────────────────────────────────────────────
def get_id(record: dict):
    return record.get("id") or record.get("cycle_id")


def update_dataset(session: requests.Session, name: str, endpoint: str) -> list:
    existing = load_saved(name)
    if not existing:
        print(f"  No existing data — fetching all.")
        new_records = paginate(session, endpoint)
        save(name, new_records)
        return new_records

    since = latest_start(existing)
    if not since:
        print(f"  Could not determine latest date — fetching all.")
        new_records = paginate(session, endpoint)
        save(name, new_records)
        return new_records

    print(f"  Fetching records since {since[:10]}...")
    new_records = paginate(session, endpoint, params={"start": since})

    if not new_records:
        print(f"  Already up to date ({len(existing)} records).")
        return existing

    seen   = {get_id(r) for r in new_records}
    merged = new_records + [r for r in existing if get_id(r) not in seen]
    added  = len(merged) - len(existing)
    print(f"  Added {added} new record(s). Total: {len(merged)}.")
    save(name, merged)
    return merged


# ── Fetch all data ────────────────────────────────────────────────────────────
def fetch_all(session: requests.Session, update: bool = False):
    print("\n── Profile ──────────────────────────────────")
    profile = fetch_single(session, "/user/profile/basic")
    save("profile", profile)

    print("\n── Body Measurements ────────────────────────")
    body = fetch_single(session, "/user/measurement/body")
    save("body_measurement", body)

    if update:
        print("\n── Cycles (daily strain) ────────────────────")
        cycles = update_dataset(session, "cycles", "/cycle")

        print("\n── Recovery ─────────────────────────────────")
        recovery = update_dataset(session, "recovery", "/recovery")

        print("\n── Sleep ────────────────────────────────────")
        sleep = update_dataset(session, "sleep", "/activity/sleep")

        print("\n── Workouts ─────────────────────────────────")
        workouts = update_dataset(session, "workouts", "/activity/workout")
    else:
        print("\n── Cycles (daily strain) ────────────────────")
        cycles = load_saved("cycles")
        if cycles is not None:
            print(f"  Skipping — {len(cycles)} records already saved.")
        else:
            cycles = paginate(session, "/cycle")
            save("cycles", cycles)

        print("\n── Recovery ─────────────────────────────────")
        recovery = load_saved("recovery")
        if recovery is not None:
            print(f"  Skipping — {len(recovery)} records already saved.")
        else:
            recovery = paginate(session, "/recovery")
            save("recovery", recovery)

        print("\n── Sleep ────────────────────────────────────")
        sleep = load_saved("sleep")
        if sleep is not None:
            print(f"  Skipping — {len(sleep)} records already saved.")
        else:
            sleep = paginate(session, "/activity/sleep")
            save("sleep", sleep)

        print("\n── Workouts ─────────────────────────────────")
        workouts = load_saved("workouts")
        if workouts is not None:
            print(f"  Skipping — {len(workouts)} records already saved.")
        else:
            workouts = paginate(session, "/activity/workout")
            save("workouts", workouts)

    return {
        "profile":          profile,
        "body_measurement": body,
        "cycles":           len(cycles),
        "recovery":         len(recovery),
        "sleep":            len(sleep),
        "workouts":         len(workouts),
    }


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    update_mode = "--full" not in sys.argv

    tokens  = get_valid_tokens()
    session = make_session(tokens["access_token"])

    mode_label = "incremental update" if update_mode else "full fetch"
    print(f"\nFetching WHOOP data ({datetime.now().strftime('%Y-%m-%d %H:%M')}) [{mode_label}]")
    summary = fetch_all(session, update=update_mode)

    print("\n── Summary ──────────────────────────────────")
    for k, v in summary.items():
        if isinstance(v, int):
            print(f"  {k:<20} {v} records")
        elif isinstance(v, dict):
            name = v.get("first_name", "") + " " + v.get("last_name", "")
            print(f"  {k:<20} {name.strip() or '(fetched)'}")
    print(f"\nDone! Data saved to {OUTPUT_DIR}/")
