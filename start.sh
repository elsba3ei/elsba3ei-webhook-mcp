#!/usr/bin/env bash
# =============================================================================
#  elsba3ei Webhook MCP Server - Linux / macOS Launcher
# =============================================================================

set -e

# Change to script directory
cd "$(dirname "$0")"

echo -e "\033[1;35m========================================================\033[0m"
echo -e "\033[1;32m  🤖 Starting elsba3ei Webhook FastMCP Server...\033[0m"
echo -e "\033[1;35m========================================================\033[0m"

# Ensure Python 3 is installed
if ! command -v python3 >/dev/null 2>&1; then
  echo -e "\033[1;31m[!] Error: python3 is not installed.\033[0m"
  exit 1
fi

# Create virtual environment if missing
if [ ! -d ".venv" ]; then
  echo -e "\033[1;33m[*] Creating Python virtual environment (.venv)...\033[0m"
  python3 -m venv .venv
  source .venv/bin/activate
  echo -e "\033[1;33m[*] Installing dependencies from requirements.txt...\033[0m"
  pip install --upgrade pip
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi

# Run the FastMCP server
exec python3 elsba3ei_webhook_server.py "$@"
