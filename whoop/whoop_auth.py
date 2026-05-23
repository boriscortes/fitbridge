"""
WHOOP OAuth 2.0 Authentication
Opens a browser for login, captures the callback on localhost:8080,
and saves tokens to whoop-data/whoop_tokens.json.
"""

import json
import os
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

# Load .env from fitbridge root
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

# ── Config ────────────────────────────────────────────────────────────────────
CLIENT_ID     = os.environ.get("WHOOP_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("WHOOP_CLIENT_SECRET", "")

REDIRECT_URI = "http://localhost:8080"
AUTH_URL     = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL    = "https://api.prod.whoop.com/oauth/oauth2/token"
TOKENS_FILE  = Path(__file__).parent.parent / "whoop-data" / "whoop_tokens.json"

SCOPES = [
    "offline",
    "read:recovery",
    "read:cycles",
    "read:sleep",
    "read:workout",
    "read:profile",
    "read:body_measurement",
]


# ── Local callback server ─────────────────────────────────────────────────────
class CallbackHandler(BaseHTTPRequestHandler):
    code = None
    state = None

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        CallbackHandler.code = params.get("code", [None])[0]
        CallbackHandler.state = params.get("state", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"""
            <html><body style="font-family:sans-serif;text-align:center;padding:60px">
            <h2>Authorization successful!</h2>
            <p>You can close this tab and return to the terminal.</p>
            </body></html>
        """)

    def log_message(self, *args):
        pass


def run_local_server():
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.handle_request()
    return CallbackHandler.code, CallbackHandler.state


# ── Token helpers ─────────────────────────────────────────────────────────────
def exchange_code(code: str) -> dict:
    resp = requests.post(TOKEN_URL, data={
        "grant_type":    "authorization_code",
        "code":          code,
        "redirect_uri":  REDIRECT_URI,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    return resp.json()


def refresh_tokens(refresh_token: str) -> dict:
    resp = requests.post(TOKEN_URL, data={
        "grant_type":    "refresh_token",
        "refresh_token": refresh_token,
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })
    resp.raise_for_status()
    return resp.json()


def save_tokens(tokens: dict):
    import time
    tokens["saved_at"] = time.time()
    TOKENS_FILE.parent.mkdir(exist_ok=True)
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    print(f"Tokens saved to {TOKENS_FILE}")


def load_tokens() -> dict | None:
    if TOKENS_FILE.exists():
        with open(TOKENS_FILE) as f:
            return json.load(f)
    return None


# ── Main auth flow ────────────────────────────────────────────────────────────
def authenticate():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError(
            "Set WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET in .env\n"
            "Create a developer app at https://developer.whoop.com"
        )

    state = secrets.token_urlsafe(16)
    params = urlencode({
        "response_type": "code",
        "client_id":     CLIENT_ID,
        "redirect_uri":  REDIRECT_URI,
        "scope":         " ".join(SCOPES),
        "state":         state,
    })
    auth_link = f"{AUTH_URL}?{params}"

    print("Opening WHOOP login in your browser...")
    print(f"\nIf the browser doesn't open, visit:\n  {auth_link}\n")
    webbrowser.open(auth_link)

    print("Waiting for authorization callback on http://localhost:8080 ...")
    code, returned_state = run_local_server()

    if not code:
        raise RuntimeError("No authorization code received.")
    if returned_state != state:
        raise RuntimeError("State mismatch — possible CSRF attack.")

    print("Authorization code received. Exchanging for tokens...")
    tokens = exchange_code(code)
    save_tokens(tokens)
    return tokens


def get_valid_tokens() -> dict:
    """Load saved tokens, refreshing if expired."""
    import time

    tokens = load_tokens()
    if tokens is None:
        print("No saved tokens found. Starting OAuth flow...")
        return authenticate()

    saved_at   = tokens.get("saved_at", 0)
    expires_in = tokens.get("expires_in", 3600)
    if time.time() - saved_at < expires_in - 60:
        return tokens

    if "refresh_token" in tokens and CLIENT_SECRET:
        try:
            print("Access token expired. Refreshing...")
            tokens = refresh_tokens(tokens["refresh_token"])
            save_tokens(tokens)
            return tokens
        except requests.HTTPError as e:
            print(f"Refresh failed ({e}). Re-authenticating...")
            return authenticate()

    return tokens


if __name__ == "__main__":
    tokens = get_valid_tokens()
    print("\nAccess token obtained successfully.")
    print(f"Token type : {tokens.get('token_type')}")
    print(f"Expires in : {tokens.get('expires_in')} seconds")
    print(f"Scopes     : {tokens.get('scope')}")
