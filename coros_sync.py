#!/usr/bin/env python3
"""
fitbridge: sync COROS activities to Strava, Garmin Connect, and TrainingPeaks.

- Downloads only NEW FIT files from COROS (not already in exports dir)
- Validates no duplicate on Strava (±1 min start time check)
- Skips walks by default (use --walks to include them)
- Uploads to any combination of Strava, Garmin, and TrainingPeaks

Usage:
    python3 coros_sync.py              # sync today → all platforms
    python3 coros_sync.py --days 7    # sync last 7 days
    python3 coros_sync.py --strava    # Strava only
    python3 coros_sync.py --garmin    # Garmin only
    python3 coros_sync.py --tp        # TrainingPeaks only
    python3 coros_sync.py --walks     # include walks
    python3 coros_sync.py --file path.fit  # direct one-off upload
"""
import asyncio
import re
import sys
import time
import logging
import argparse
import subprocess
import requests
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import date, datetime, timezone, timedelta
from fitparse import FitFile
from garminconnect import Garmin

# Silence garminconnect's internal login-strategy WARNINGs (mobile+cffi falling
# back to mobile+requests). Real errors still raise exceptions caught below.
logging.getLogger('garminconnect').setLevel(logging.ERROR)
logging.getLogger('garminconnect.client').setLevel(logging.ERROR)

ENV_PATH      = Path(__file__).parent / '.env'
EXPORTS_DIR   = Path(__file__).parent / 'coros-exports'
COROS_API_DIR = Path(__file__).parent / 'coros-api'
LOG_DIR       = Path(__file__).parent / 'logs'
SKIP_KEYWORDS = ['Walk', 'walk']

LOG_DIR.mkdir(exist_ok=True)
_log_handler = RotatingFileHandler(LOG_DIR / 'coros_sync.log', maxBytes=1_000_000, backupCount=3)
_log_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
logger = logging.getLogger('coros_sync')
logger.setLevel(logging.INFO)
logger.addHandler(_log_handler)


# ── ENV ──────────────────────────────────────────────────────────────────────

def load_env():
    if not ENV_PATH.exists():
        return {}
    env = ENV_PATH.read_text()
    def get(pattern):
        m = re.search(pattern, env)
        return m.group(1) if m else None
    return {
        'strava_client_id':     get(r'STRAVA_CLIENT_ID=(\S+)'),
        'strava_client_secret': get(r'STRAVA_CLIENT_SECRET=(\S+)'),
        'strava_access_token':  get(r'STRAVA_ACCESS_TOKEN=(\S+)'),
        'strava_refresh_token': get(r'STRAVA_REFRESH_TOKEN=(\S+)'),
        'garmin_email':         get(r'GARMIN_EMAIL=(\S+)'),
        'garmin_password':      get(r'GARMIN_PASSWORD=(\S+)'),
        'tp_mcp_path':          get(r'TP_MCP_PATH=(\S+)'),
    }


# ── STRAVA ───────────────────────────────────────────────────────────────────

def strava_refresh():
    creds = load_env()
    r = requests.post('https://www.strava.com/oauth/token', data={
        'client_id':     creds['strava_client_id'],
        'client_secret': creds['strava_client_secret'],
        'refresh_token': creds['strava_refresh_token'],
        'grant_type':    'refresh_token',
    })
    r.raise_for_status()
    data = r.json()
    env = ENV_PATH.read_text()
    env = re.sub(r'STRAVA_ACCESS_TOKEN=\S+',  f"STRAVA_ACCESS_TOKEN={data['access_token']}",  env)
    env = re.sub(r'STRAVA_REFRESH_TOKEN=\S+', f"STRAVA_REFRESH_TOKEN={data['refresh_token']}", env)
    ENV_PATH.write_text(env)
    return data['access_token']


def strava_get(token, endpoint, params=None):
    r = requests.get(f'https://www.strava.com/api/v3/{endpoint}',
                     headers={'Authorization': f'Bearer {token}'}, params=params or {})
    if r.status_code == 401:
        return strava_get(strava_refresh(), endpoint, params)
    r.raise_for_status()
    return r.json()


def strava_has_duplicate(token, start_time_utc, tolerance=60):
    after  = int((start_time_utc - timedelta(hours=1)).timestamp())
    before = int((start_time_utc + timedelta(hours=2)).timestamp())
    acts   = strava_get(token, 'athlete/activities', {'after': after, 'before': before, 'per_page': 30})
    for a in acts:
        act_start = datetime.fromisoformat(a['start_date'].replace('Z', '+00:00'))
        if abs((act_start - start_time_utc).total_seconds()) <= tolerance:
            return True, f"{a['name']} (id={a['id']})"
    return False, None


SPORT_MAP = {
    'strength':    'weighttraining',
    'run':         'run',
    'indoorrun':   'run',
    'indoor run':  'run',
    'trailrun':    'run',
    'trail run':   'run',
    'hike':        'hike',
    'indoorbike':  'virtualride',
    'indoor bike': 'virtualride',
    'bike':        'ride',
    'walk':        'walk',
}

def detect_sport(fit_path: Path) -> str:
    name = fit_path.name.lower()
    for keyword, strava_type in SPORT_MAP.items():
        if keyword in name:
            return strava_type
    return 'workout'


def activity_name_from_filename(fit_path: Path) -> str:
    """Extract activity name from COROS filename: '2026-05-22 Easy Run - 13 km[2] 477673....fit'"""
    stem = fit_path.stem
    stem = re.sub(r'^\d{4}-\d{2}-\d{2}\s+', '', stem)   # drop leading date
    stem = re.sub(r'\s+\d{15,}\s*$', '', stem)            # drop trailing COROS ID
    stem = re.sub(r'\[\d\]$', '', stem)                   # drop Fuelin tag e.g. [2]
    return stem.strip()


def strava_upload(token, fit_path):
    sport = detect_sport(fit_path)
    name  = activity_name_from_filename(fit_path)
    with open(fit_path, 'rb') as f:
        r = requests.post('https://www.strava.com/api/v3/uploads',
                          headers={'Authorization': f'Bearer {token}'},
                          data={
                              'data_type': 'fit',
                              'activity_type': sport,
                              'name': name,
                              'private': '0',
                              'visibility': 'followers_only',
                          },
                          files={'file': (fit_path.name, f, 'application/octet-stream')})
    if r.status_code == 401:
        return strava_upload(strava_refresh(), fit_path)
    return r.json()


def strava_poll(token, upload_id, retries=10):
    for _ in range(retries):
        time.sleep(2)
        r = requests.get(f'https://www.strava.com/api/v3/uploads/{upload_id}',
                         headers={'Authorization': f'Bearer {token}'})
        data = r.json()
        if data.get('error'):       return None, data['error']
        if data.get('activity_id'): return data['activity_id'], None
    return None, 'timeout'


def strava_set_visibility(token, activity_id, visibility='followers_only'):
    r = requests.put(
        f'https://www.strava.com/api/v3/activities/{activity_id}',
        headers={'Authorization': f'Bearer {token}'},
        data={'visibility': visibility}
    )
    return r.json().get('visibility') == visibility


# ── GARMIN ───────────────────────────────────────────────────────────────────

def garmin_login():
    creds = load_env()
    client = Garmin(creds['garmin_email'], creds['garmin_password'])
    client.login()
    return client


# ── TRAININGPEAKS ─────────────────────────────────────────────────────────────

def _load_tp_client(tp_mcp_path: str):
    """Import TPClient from a local trainingpeaks-mcp install."""
    path = Path(tp_mcp_path).expanduser() / 'src'
    if not path.exists():
        raise ImportError(f"trainingpeaks-mcp not found at {path}. Set TP_MCP_PATH in .env.")
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    from tp_mcp.client import TPClient  # noqa: PLC0415
    from tp_mcp.tools.workout_files import tp_upload_workout_file  # noqa: PLC0415
    return TPClient, tp_upload_workout_file


TP_SPORT_MAP = {
    'run':           'Run',
    'trailrun':      'Run',
    'indoorrun':     'Run',
    'hike':          'Hike',
    'bike':          'Bike',
    'indoorbike':    'Bike',
    'strength':      'Strength',
    'walk':          'Walk',
}

def _tp_sport(fit_path: Path) -> str:
    name = fit_path.name.lower()
    for kw, tp_type in TP_SPORT_MAP.items():
        if kw in name:
            return tp_type
    return 'Other'


async def tp_upload(fit_path: Path, tp_mcp_path: str):
    """Create a blank TP workout for the activity date, then attach the FIT file."""
    try:
        TPClient, tp_upload_workout_file = _load_tp_client(tp_mcp_path)
    except ImportError as e:
        return False, str(e)

    start_time = get_fit_start_time(fit_path)
    if not start_time:
        return False, 'no start time in FIT'

    workout_day = start_time.astimezone().strftime('%Y-%m-%d')
    sport       = _tp_sport(fit_path)
    name        = activity_name_from_filename(fit_path)

    async with TPClient() as client:
        athlete_id = await client.ensure_athlete_id()
        if not athlete_id:
            return False, 'TP auth invalid — run: tp-mcp auth'

        # Step 1: create blank workout to get a workout_id
        create_resp = await client.post(
            f'/fitness/v6/athletes/{athlete_id}/workouts',
            json={
                'workoutDay': f'{workout_day}T00:00:00',
                'workoutTypeValueId': 3 if sport == 'Run' else 1,
                'title': name,
            }
        )
        if create_resp.is_error:
            return False, f'create workout failed: {create_resp.message}'

        workout_id = str(create_resp.data.get('workoutId') or create_resp.data.get('id', ''))
        if not workout_id:
            return False, 'no workout_id in create response'

        # Step 2: attach the FIT file
        result = await tp_upload_workout_file(
            workout_id=workout_id,
            file_path=str(fit_path),
            workout_day=workout_day,
        )
        if result.get('isError'):
            return False, result.get('message', 'upload failed')

    return True, workout_id


# ── FIT ──────────────────────────────────────────────────────────────────────

def get_fit_start_time(fit_path):
    fit = FitFile(str(fit_path))
    for record in fit.get_messages('record'):
        data = {f.name: f.value for f in record.fields}
        if data.get('timestamp'):
            return data['timestamp'].replace(tzinfo=timezone.utc)
    return None


# ── COROS ────────────────────────────────────────────────────────────────────

def coros_export(from_date, to_date):
    """Export all sport types from COROS and return only newly downloaded files."""
    EXPORTS_DIR.mkdir(exist_ok=True)
    existing = {f.name for f in EXPORTS_DIR.glob('*.fit')}

    sport_types = 'run,indoorRun,trailRun,trackRun,hike,bike,indoorBike,strength,gymCardio,gpsCardio,walk'

    print(f"📡 Downloading from COROS ({from_date} → {to_date})...")
    logger.info(f"COROS export {from_date} → {to_date}")
    subprocess.run(
        ['pnpm', 'nest', 'start', '--', 'export-activities',
         '--fromDate', from_date, '--toDate', to_date,
         '--exportSportTypes', sport_types,
         '-o', str(EXPORTS_DIR)],
        cwd=str(COROS_API_DIR), capture_output=True, text=True
    )

    new_files = [f for f in sorted(EXPORTS_DIR.glob('*.fit')) if f.name not in existing]
    print(f"   {len(new_files)} new file(s) downloaded")
    logger.info(f"Downloaded {len(new_files)} new file(s)")
    return new_files


# ── MAIN SYNC ─────────────────────────────────────────────────────────────────

def process_file(fit_path, strava_token=None, garmin_client=None, tp_mcp_path=None, force=False):
    filename = fit_path.name

    # Skip walks (bypass with force=True for --walks flag or direct --file uploads)
    if not force and any(kw in filename for kw in SKIP_KEYWORDS):
        print(f"  ⏭️  Skip (walk): {filename}")
        logger.info(f"Skipped walk: {filename}")
        return

    start_time = get_fit_start_time(fit_path)
    if not start_time:
        print(f"  ❌ No start time in FIT: {filename}")
        logger.error(f"No start time in FIT: {filename}")
        return

    local_time = start_time.astimezone().strftime('%I:%M %p %Z')
    print(f"\n  📁 {filename[:60]}")
    sport = detect_sport(fit_path)
    print(f"     Start: {local_time} | Sport: {sport}")
    logger.info(f"Processing: {filename} | {local_time} | {sport}")

    # ── Strava ──
    if strava_token:
        is_dup, dup_info = strava_has_duplicate(strava_token, start_time)
        if is_dup:
            print(f"     Strava: ⏭️  duplicate ({dup_info})")
            logger.info(f"Strava duplicate: {filename} ({dup_info})")
        else:
            result = strava_upload(strava_token, fit_path)
            if result.get('error'):
                print(f"     Strava: ❌ {result['error']}")
                logger.error(f"Strava upload error: {filename} — {result['error']}")
            else:
                act_id, err = strava_poll(strava_token, result['id'])
                if act_id:
                    strava_set_visibility(strava_token, act_id)
                    print(f"     Strava: ✅ strava.com/activities/{act_id} (followers only)")
                    logger.info(f"Strava uploaded: {filename} → activity/{act_id}")
                else:
                    print(f"     Strava: ❌ {err}")
                    logger.error(f"Strava poll failed: {filename} — {err}")

    # ── Garmin ──
    if garmin_client:
        for attempt in range(3):
            try:
                garmin_client.upload_activity(str(fit_path))
                print(f"     Garmin: ✅ uploaded")
                logger.info(f"Garmin uploaded: {filename}")
                break
            except Exception as e:
                if '409' in str(e) or 'duplicate' in str(e).lower():
                    print(f"     Garmin: ⏭️  duplicate")
                    logger.info(f"Garmin duplicate: {filename}")
                    break
                if attempt < 2:
                    time.sleep(5)
                else:
                    print(f"     Garmin: ❌ {e}")
                    logger.error(f"Garmin failed: {filename} — {e}")

    # ── TrainingPeaks ──
    if tp_mcp_path:
        ok, info = asyncio.run(tp_upload(fit_path, tp_mcp_path))
        if ok:
            print(f"     TrainingPeaks: ✅ workout/{info}")
            logger.info(f"TP uploaded: {filename} → workout/{info}")
        else:
            print(f"     TrainingPeaks: ❌ {info}")
            logger.error(f"TP failed: {filename} — {info}")


def main():
    parser = argparse.ArgumentParser(description='Sync COROS activities to Strava, Garmin, and TrainingPeaks')
    parser.add_argument('--days',   type=int, default=0,  help='Sync last N days (default: today only)')
    parser.add_argument('--strava', action='store_true',  help='Upload to Strava only')
    parser.add_argument('--garmin', action='store_true',  help='Upload to Garmin only')
    parser.add_argument('--tp',     action='store_true',  help='Upload to TrainingPeaks only')
    parser.add_argument('--force',  action='store_true',  help='Reprocess all files for the date range')
    parser.add_argument('--file',   metavar='PATH',       help='Upload a specific FIT file directly')
    parser.add_argument('--walks',  action='store_true',  help='Include walks (skipped by default)')
    args = parser.parse_args()

    creds    = load_env()
    any_flag = args.strava or args.garmin or args.tp

    do_strava = args.strava or not any_flag
    do_garmin = args.garmin or not any_flag
    do_tp     = args.tp     or (not any_flag and bool(creds.get('tp_mcp_path')))

    tp_mcp_path = creds.get('tp_mcp_path') if do_tp else None

    # --file: direct upload of a specific FIT file, bypassing COROS export and walk-skip
    if args.file:
        fit_path = Path(args.file)
        if not fit_path.exists():
            print(f"❌ File not found: {args.file}")
            return
        strava_token  = strava_refresh() if do_strava else None
        garmin_client = None
        if do_garmin:
            try:
                print("🔐 Logging into Garmin Connect...")
                garmin_client = garmin_login()
                print("   ✅ Logged in")
            except Exception as e:
                print(f"   ❌ Garmin login failed: {e}")
        print(f"\nProcessing 1 file (direct)...")
        process_file(fit_path, strava_token=strava_token, garmin_client=garmin_client,
                     tp_mcp_path=tp_mcp_path, force=True)
        print("\n✅ Done.")
        return

    today     = date.today().strftime('%Y-%m-%d')
    from_date = (date.today() - timedelta(days=args.days)).strftime('%Y-%m-%d') if args.days else today

    # Step 1: Download new files from COROS
    if args.force:
        coros_export(from_date, today)
        new_files = [f for f in sorted(EXPORTS_DIR.glob('*.fit')) if from_date <= f.name[:10] <= today]
        print(f"   --force: processing {len(new_files)} file(s) in date range")
    else:
        new_files = coros_export(from_date, today)

    if not new_files:
        print("✅ No new files to upload.")
        return

    # Step 2: Login to platforms
    strava_token  = strava_refresh() if do_strava else None
    garmin_client = None
    if do_garmin:
        try:
            print("🔐 Logging into Garmin Connect...")
            garmin_client = garmin_login()
            print("   ✅ Logged in")
        except Exception as e:
            print(f"   ❌ Garmin login failed: {e}")

    # Step 3: Process each new file
    print(f"\nProcessing {len(new_files)} new file(s)...")
    for f in new_files:
        process_file(f, strava_token=strava_token, garmin_client=garmin_client,
                     tp_mcp_path=tp_mcp_path, force=args.walks)

    print("\n✅ Sync complete.")


if __name__ == '__main__':
    main()
