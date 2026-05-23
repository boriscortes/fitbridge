#!/usr/bin/env python3
"""
Strava OAuth token exchange helper.

Reads STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET from .env,
prints the authorization URL, waits for the redirect URL from
the user, exchanges the code for tokens, and writes them to .env.

Usage:
    python3 tools/strava_oauth.py
"""
import re
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

try:
    import requests
except ImportError:
    sys.exit("requests not installed — run: pip install requests")

ENV_PATH = Path(__file__).parent.parent / '.env'

REDIRECT_URI = 'http://localhost'
SCOPE        = 'activity:read_all,activity:write'


def read_env(key):
    if not ENV_PATH.exists():
        return None
    m = re.search(rf'^{key}=(\S+)', ENV_PATH.read_text(), re.MULTILINE)
    return m.group(1) if m else None


def write_env(key, value):
    text = ENV_PATH.read_text() if ENV_PATH.exists() else ''
    pattern = rf'^{key}=.*$'
    new_line = f'{key}={value}'
    if re.search(pattern, text, re.MULTILINE):
        text = re.sub(pattern, new_line, text, flags=re.MULTILINE)
    else:
        text = text.rstrip('\n') + f'\n{new_line}\n'
    ENV_PATH.write_text(text)


def main():
    client_id     = read_env('STRAVA_CLIENT_ID')
    client_secret = read_env('STRAVA_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("❌  STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET must be set in .env first.")
        print()
        print("   1. Go to https://www.strava.com/settings/api")
        print("   2. Create an app (Authorization Callback Domain: localhost)")
        print("   3. Copy Client ID and Client Secret into .env")
        print("   4. Re-run this script")
        sys.exit(1)

    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&approval_prompt=force"
        f"&scope={SCOPE}"
    )

    print()
    print("Opening Strava authorization in your browser...")
    print(f"   {auth_url}")
    print()
    webbrowser.open(auth_url)

    print("After authorizing, your browser will redirect to a URL like:")
    print("   http://localhost/?state=&code=abc123...&scope=...")
    print()
    redirect = input("Paste the full redirect URL here: ").strip()

    parsed = urlparse(redirect)
    params = parse_qs(parsed.query)
    code   = params.get('code', [None])[0]

    if not code:
        sys.exit("❌  No code found in the URL. Make sure you paste the full redirect URL.")

    print()
    print("Exchanging code for tokens...")
    r = requests.post('https://www.strava.com/oauth/token', data={
        'client_id':     client_id,
        'client_secret': client_secret,
        'code':          code,
        'grant_type':    'authorization_code',
    })
    r.raise_for_status()
    data = r.json()

    write_env('STRAVA_ACCESS_TOKEN',  data['access_token'])
    write_env('STRAVA_REFRESH_TOKEN', data['refresh_token'])

    athlete = data.get('athlete', {})
    name    = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
    print(f"✅  Authenticated as: {name or 'unknown athlete'}")
    print("   STRAVA_ACCESS_TOKEN and STRAVA_REFRESH_TOKEN written to .env")


if __name__ == '__main__':
    main()
