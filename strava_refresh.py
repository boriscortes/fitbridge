#!/usr/bin/env python3
"""
Refresh Strava access token using refresh token.
Run this when access token expires (every 6 hours).
Updates .env file automatically.
"""
import requests
import re
from pathlib import Path

ENV_PATH = Path(__file__).parent / '.env'

def refresh_token():
    env = ENV_PATH.read_text()

    client_id     = re.search(r'STRAVA_CLIENT_ID=(\S+)', env).group(1)
    client_secret = re.search(r'STRAVA_CLIENT_SECRET=(\S+)', env).group(1)
    refresh_token = re.search(r'STRAVA_REFRESH_TOKEN=(\S+)', env).group(1)

    r = requests.post('https://www.strava.com/oauth/token', data={
        'client_id':     client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type':    'refresh_token',
    })
    r.raise_for_status()
    data = r.json()

    new_access  = data['access_token']
    new_refresh = data['refresh_token']

    env = re.sub(r'STRAVA_ACCESS_TOKEN=\S+',  f'STRAVA_ACCESS_TOKEN={new_access}',  env)
    env = re.sub(r'STRAVA_REFRESH_TOKEN=\S+', f'STRAVA_REFRESH_TOKEN={new_refresh}', env)
    ENV_PATH.write_text(env)

    print(f"✅ Token refreshed. New access token: {new_access[:20]}...")
    return new_access

def get_token():
    """Get current access token, refreshing if needed."""
    env = ENV_PATH.read_text()
    return re.search(r'STRAVA_ACCESS_TOKEN=(\S+)', env).group(1)

def strava_get(endpoint, params=None):
    """Make authenticated GET request to Strava API, auto-refreshing token."""
    token = get_token()
    r = requests.get(
        f'https://www.strava.com/api/v3/{endpoint}',
        headers={'Authorization': f'Bearer {token}'},
        params=params or {}
    )
    if r.status_code == 401:
        print("Token expired, refreshing...")
        token = refresh_token()
        r = requests.get(
            f'https://www.strava.com/api/v3/{endpoint}',
            headers={'Authorization': f'Bearer {token}'},
            params=params or {}
        )
    r.raise_for_status()
    return r.json()

if __name__ == '__main__':
    refresh_token()
