#!/usr/bin/env bash
set -uo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
RESET='\033[0m'

ok()   { echo -e "  ${GREEN}✅${RESET} $1"; }
fail() { echo -e "  ${RED}❌${RESET} $1"; }
warn() { echo -e "  ${YELLOW}⚠️ ${RESET} $1"; }

echo ""
echo -e "${BOLD}fitbridge setup${RESET}"
echo "─────────────────────────────────────"

# ── Prerequisites ─────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}Prerequisites${RESET}"

# Python ≥ 3.9
if command -v python3 &>/dev/null; then
    PYVER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYOK=$(python3 -c 'import sys; print(int(sys.version_info >= (3,9)))')
    if [ "$PYOK" = "1" ]; then
        ok "Python $PYVER"
    else
        fail "Python $PYVER (need ≥ 3.9)"
        echo "     → Install: https://python.org/downloads"
        PREREQ_FAIL=1
    fi
else
    fail "Python 3 not found"
    echo "     → Install: https://python.org/downloads"
    PREREQ_FAIL=1
fi

# Node.js
if command -v node &>/dev/null; then
    ok "Node.js $(node --version)"
else
    fail "Node.js not found"
    echo "     → Install: https://nodejs.org or: brew install node"
    PREREQ_FAIL=1
fi

# pnpm
if command -v pnpm &>/dev/null; then
    ok "pnpm $(pnpm --version)"
else
    fail "pnpm not found"
    echo "     → Install: npm install -g pnpm"
    PREREQ_FAIL=1
fi

if [ "${PREREQ_FAIL:-0}" = "1" ]; then
    echo ""
    echo -e "${RED}Fix the above prerequisites before continuing.${RESET}"
    exit 1
fi

# ── Python dependencies ────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}Python dependencies${RESET}"
if python3 -m pip install fitparse garminconnect requests -q 2>/dev/null; then
    ok "fitparse, garminconnect, requests installed"
else
    fail "pip install failed"
    echo "     → Try: python3 -m pip install fitparse garminconnect requests"
fi

# ── COROS API wrapper ──────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}COROS API wrapper${RESET}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/coros-api" ] && [ -f "$SCRIPT_DIR/coros-api/package.json" ]; then
    if (cd "$SCRIPT_DIR/coros-api" && pnpm install --silent 2>/dev/null); then
        ok "coros-api dependencies installed"
    else
        fail "pnpm install failed in coros-api/"
    fi
else
    fail "coros-api/ not found — did you clone with --recurse-submodules?"
    echo "     → Fix: git submodule update --init"
fi

# ── .env ──────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}.env${RESET}"
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    ok "Created .env from .env.example"
    warn "Fill in your credentials — run /setup in Claude Code to be guided through it"
else
    ok "Found .env"
fi

# ── Credential readiness (informational) ──────────────────────────────────────

echo ""
echo -e "${BOLD}Credential status${RESET}"

check_env() {
    local label=$1; shift
    local missing=0
    for key in "$@"; do
        val=$(grep -E "^${key}=(.+)" "$SCRIPT_DIR/.env" 2>/dev/null | cut -d= -f2- | tr -d '[:space:]')
        [ -z "$val" ] && missing=1
    done
    if [ "$missing" = "0" ]; then ok "$label"; else warn "$label — not configured yet"; fi
}

check_env "COROS"          COROS_EMAIL COROS_PASSWORD
check_env "Strava"         STRAVA_CLIENT_ID STRAVA_CLIENT_SECRET STRAVA_ACCESS_TOKEN STRAVA_REFRESH_TOKEN
check_env "Garmin"         GARMIN_EMAIL GARMIN_PASSWORD
check_env "TrainingPeaks"  TP_MCP_PATH

echo ""
echo -e "${BOLD}Done.${RESET} Run ${BOLD}/setup${RESET} in Claude Code to configure credentials."
echo ""
