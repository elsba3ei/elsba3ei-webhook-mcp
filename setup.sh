#!/usr/bin/env bash
# =============================================================================
#  elsba3ei Webhook MCP Server - Linux / macOS Automated Docker & venv Setup
# =============================================================================

set -e

cd "$(dirname "$0")"

echo -e "\033[1;35m========================================================\033[0m"
echo -e "\033[1;35m  elsba3ei Webhook MCP Server - Linux & macOS Setup\033[0m"
echo -e "\033[1;35m========================================================\033[0m"

# 1. Python Local Environment Setup
echo -e "\n\033[1;36m=== Step 1: Setting up Python Virtual Environment ===\033[0m"
if command -v python3 >/dev/null 2>&1; then
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  echo -e "\033[1;32m  [OK] Python virtual environment ready at $(pwd)/.venv\033[0m"
else
  echo -e "\033[1;33m  [INFO] python3 not found, skipping local venv.\033[0m"
fi

# 2. Docker Setup (Optional)
echo -e "\n\033[1;36m=== Step 2: Docker Build (Optional) ===\033[0m"
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    docker build -t elsba3ei-webhook:latest .
    echo -e "\033[1;32m  [OK] Docker image elsba3ei-webhook:latest built.\033[0m"
    
    # Try Docker MCP profile if supported
    CATALOG_PATH="file://$(pwd)/elsba3ei-webhook-catalog.yaml"
    docker mcp profile server add default --server "$CATALOG_PATH" 2>/dev/null || true
  else
    echo -e "\033[1;33m  [INFO] Docker daemon is not running.\033[0m"
  fi
fi

echo -e "\n\033[1;32m========================================================\033[0m"
echo -e "\033[1;32m  Setup Complete!\033[0m"
echo -e "\033[1;33m  Run './start.sh' to launch the server.\033[0m"
echo -e "\033[1;32m========================================================\033[0m"
