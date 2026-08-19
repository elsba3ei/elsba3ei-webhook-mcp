# elsba3ei Webhook MCP Server

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org/)
[![FastMCP](https://img.shields.io/badge/MCP-FastMCP-8A2BE2?style=flat-square&logo=anthropic&logoColor=white)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](https://opensource.org/licenses/MIT)

**High-performance local & public Webhook Inspector and Burp Suite Collaborator alternative for testing SSRF, APIs, and Out-Of-Band (OOB) interactions with Cloudflare Quick Tunnel support, dynamic mock responses, live request capture, and callback polling for AI coding agents.**

---

## Overview & Capabilities

The `elsba3ei-webhook-mcp` server connects **all major LLM models and AI coding agents** (tested & verified with **ChatGPT / OpenAI Codex**, **Anthropic Claude**, **Google Antigravity**, and **Cursor / Windsurf**) to:

- Instantly spin up local (`http://127.0.0.1:4040/capture`) and public Cloudflare Quick Tunnels (`https://*.trycloudflare.com/capture`) with no account needed.
- Inspect incoming HTTP/HTTPS requests (method, headers, query, client IP, JSON, form data, raw text, or binary hex dump).
- Dynamically mock responses with custom status codes, content-types, headers, and simulated response latency.
- Poll & block waiting for out-of-band SSRF / webhook callbacks (`wait_for_request`).
- Replay and forge custom HTTP requests (`replay_request`).

### Verified LLM & Agent Compatibility:
- **ChatGPT & OpenAI Codex**: Automated webhook testing & live interaction loops.
- **Anthropic Claude (Claude Desktop & API)**: FastMCP tool execution.
- **Google Antigravity**: Agent skill and reactive tool call integration.
- **Cursor & Windsurf IDEs**: In-editor OOB callback capture and repeater.

---

## System Requirements & Prerequisites

| Requirement | Version / Details | Purpose |
| :--- | :--- | :--- |
| **Python** | Version 3.10 or higher | Runs the FastMCP server. |
| **pip** | Latest | Installs dependencies (`httpx`, `aiohttp`, `mcp`). |
| **Cloudflared CLI** *(Optional)* | Latest | Required only if you want temporary public HTTPS tunnels. |

### Installing Cloudflared CLI (Optional for Public Tunnels):

- **Windows**:
  ```powershell
  winget install --id Cloudflare.cloudflared
  ```
- **Linux (Ubuntu / Debian)**:
  ```bash
  curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
  sudo dpkg -i cloudflared.deb
  ```
- **macOS**:
  ```bash
  brew install cloudflared
  ```

---

## Quick Start Setup

> **No Docker Required**: This server runs natively with standard Python.

### Windows Setup (PowerShell)
```powershell
cd G:\Playing\elsba3ei-webhook-mcp
.\setup.ps1
```

### Linux (Ubuntu / Debian) Setup
```bash
# 1. Install Python3 & venv
sudo apt update && sudo apt install -y python3 python3-venv python3-pip

# 2. Make scripts executable and run
cd elsba3ei-webhook-mcp
chmod +x start.sh setup.sh
./start.sh
```

### macOS Setup
```bash
cd elsba3ei-webhook-mcp
chmod +x start.sh setup.sh
./start.sh
```

---

## MCP Client Configuration (Claude Desktop, Cursor, Antigravity)

Connect the MCP server to your AI assistant using direct Python execution.

### Windows (`%APPDATA%\Claude\claude_desktop_config.json` or `.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "elsba3ei-webhook": {
      "command": "G:\\Playing\\elsba3ei-webhook-mcp\\.venv\\Scripts\\python.exe",
      "args": ["G:\\Playing\\elsba3ei-webhook-mcp\\elsba3ei_webhook_server.py"]
    }
  }
}
```

### Linux & macOS (`~/.config/Claude/claude_desktop_config.json` or `~/.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "elsba3ei-webhook": {
      "command": "/path/to/elsba3ei-webhook-mcp/.venv/bin/python",
      "args": ["/path/to/elsba3ei-webhook-mcp/elsba3ei_webhook_server.py"]
    }
  }
}
```

---

## Available MCP Tools Reference

| # | Tool Name | Parameters | Description |
| :--- | :--- | :--- | :--- |
| 1 | `get_webhook_urls` | `_dummy=""` | Returns all available localhost, LAN, and public Cloudflare capture URLs. |
| 2 | `start_tunnel` | `port="4040"` | Launches a temporary Cloudflare Quick Tunnel to expose port 4040 publicly. |
| 3 | `stop_tunnel` | `_dummy=""` | Terminates the Cloudflare tunnel subprocess. |
| 4 | `get_tunnel_status` | `_dummy=""` | Returns the active tunnel URL, status, and uptime. |
| 5 | `list_requests` | `limit="20"`, `method=""`, `path_filter=""` | Summarizes captured requests with metadata. |
| 6 | `get_request_details` | `request_id="<uuid>"` | Fetches full headers, parsed/raw body, and client IP of a request ID. |
| 7 | `wait_for_request` | `timeout_seconds="30"`, `path_contains=""`, `method=""`, `body_contains=""` | Polls until an incoming request matches path, method, or body within a timeout. |
| 8 | `configure_mock_response` | `status_code="200"`, `content_type="application/json"`, `response_body="{...}"`, `delay_ms="0"`, `custom_headers_json="{}"` | Sets dynamic HTTP status, content-type, body, delay, and custom headers. |
| 9 | `reset_mock_response` | `_dummy=""` | Resets mock engine back to default 200 OK JSON. |
| 10 | `clear_requests` | `_dummy=""` | Purges the in-memory ring buffer of captured requests. |
| 11 | `delete_request` | `request_id="<uuid>"` | Removes a single request record by ID. |
| 12 | `replay_request` | `target_url`, `method="GET"`, `headers_json="{}"`, `body=""`, `timeout_seconds="10"` | Sends an HTTP request to any target URL and captures the response. |
| 13 | `get_server_status` | `_dummy=""` | Returns server health, active port, uptime, and captured request counts. |

---

## Optional: Docker Deployment (Alternative)

If you prefer containerized deployment with Docker:

```bash
# 1. Build Docker image
docker build -t elsba3ei-webhook:latest .

# 2. Run container
docker run -i --rm -p 4040:4040 elsba3ei-webhook:latest
```

*Docker MCP Configuration:*
```json
{
  "mcpServers": {
    "elsba3ei-webhook": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-p",
        "4040:4040",
        "elsba3ei-webhook:latest"
      ]
    }
  }
}
```

---

## Troubleshooting Matrix

| Symptom | Root Cause | Fix |
| :--- | :--- | :--- |
| `docker mcp catalog import not recognized` | Command removed in Docker Desktop 4.40+ | Use `docker mcp profile server add default --server file://...` instead |
| `docker mcp server enable not recognized` | Command removed in Docker Desktop 4.40+ | Replaced by `docker mcp profile server add` |
| `docker mcp client connect fails: missing flag` | `--profile` is now required | Use `docker mcp client connect claude-desktop --global --profile default` |
| Tools not appearing in Claude | Process uses wrong Docker context | Add `--context desktop-linux` to docker run args |
| "gateway panic" / Tools vanish | Multi-line tool docstring | Keep ALL `@mcp.tool()` docstrings to exactly one line |
| Port conflict on 4000/4040 | Port already occupied | Set `WEBHOOK_PORT=4041` in environment |
| Tool shows "not loaded yet" | Cache from previous session | Restart Claude Desktop + start a new conversation |

---

## Author & Developer

Developed by **Ahmed E. El-Sbaei**

- **LinkedIn**: [Ahmed E. El-Sbaei](https://www.linkedin.com/in/elsba3ei)
- **GitHub**: [@elsba3ei](https://github.com/elsba3ei)

---

## License

Distributed under the **MIT License** — © 2026 **elsba3ei**.

<div align="center">
  Developed by <b>Ahmed E. El-Sbaei</b> — © 2026 <b>elsba3ei</b> • <a href="https://www.linkedin.com/in/elsba3ei">LinkedIn</a> • <a href="https://github.com/elsba3ei">GitHub</a>
</div>
