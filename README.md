# 🤖 elsba3ei Webhook MCP Server

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![FastMCP](https://img.shields.io/badge/MCP-FastMCP-8A2BE2?style=for-the-badge&logo=anthropic&logoColor=white)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

**High-performance local & public Webhook Inspector and Burp Suite Collaborator alternative for testing SSRF, APIs, and Out-Of-Band (OOB) interactions with Cloudflare Quick Tunnel support, dynamic mock responses, live request capture, and callback polling for AI coding agents.**

---

## ⚡ Overview & Capabilities

The `elsba3ei-webhook-mcp` server allows Claude Desktop, Antigravity, and AI agents to:

- Instantly spin up local (`http://127.0.0.1:4040/capture`) and public Cloudflare Quick Tunnels (`https://*.trycloudflare.com/capture`) with no account needed.
- Inspect incoming HTTP/HTTPS requests (method, headers, query, client IP, JSON, form data, raw text, or binary hex dump).
- Dynamically mock responses with custom status codes, content-types, headers, and simulated response latency.
- Poll & block waiting for out-of-band SSRF / webhook callbacks (`wait_for_request`).
- Replay and forge custom HTTP requests (`replay_request`).

---

## 🛠️ Available MCP Tools Reference

| #      | Tool Name                 | Parameters                                                                                                                  | Description                                                                     |
| :----- | :------------------------ | :-------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------ |
| **1**  | `get_webhook_urls`        | `_dummy=""`                                                                                                                 | Returns all available localhost, LAN, and public Cloudflare capture URLs.       |
| **2**  | `start_tunnel`            | `port="4040"`                                                                                                               | Launches a temporary Cloudflare Quick Tunnel to expose port 4040 publicly.      |
| **3**  | `stop_tunnel`             | `_dummy=""`                                                                                                                 | Terminates the Cloudflare tunnel subprocess.                                    |
| **4**  | `get_tunnel_status`       | `_dummy=""`                                                                                                                 | Returns the active tunnel URL, status, and uptime.                              |
| **5**  | `list_requests`           | `limit="20"`, `method=""`, `path_filter=""`                                                                                 | Summarizes captured requests with metadata.                                     |
| **6**  | `get_request_details`     | `request_id="<uuid>"`                                                                                                       | Fetches full headers, parsed/raw body, and client IP of a request ID.           |
| **7**  | `wait_for_request`        | `timeout_seconds="30"`, `path_contains=""`, `method=""`, `body_contains=""`                                                 | Polls until an incoming request matches path, method, or body within a timeout. |
| **8**  | `configure_mock_response` | `status_code="200"`, `content_type="application/json"`, `response_body="{...}"`, `delay_ms="0"`, `custom_headers_json="{}"` | Sets dynamic HTTP status, content-type, body, delay, and custom headers.        |
| **9**  | `reset_mock_response`     | `_dummy=""`                                                                                                                 | Resets mock engine back to default 200 OK JSON.                                 |
| **10** | `clear_requests`          | `_dummy=""`                                                                                                                 | Purges the in-memory ring buffer of captured requests.                          |
| **11** | `delete_request`          | `request_id="<uuid>"`                                                                                                       | Removes a single request record by ID.                                          |
| **12** | `replay_request`          | `target_url`, `method="GET"`, `headers_json="{}"`, `body=""`, `timeout_seconds="10"`                                        | Sends an HTTP request to any target URL and captures the response.              |
| **13** | `get_server_status`       | `_dummy=""`                                                                                                                 | Returns server health, active port, uptime, and captured request counts.        |

---

## 🚀 Quick Start Setup (Windows PowerShell)

1. Open PowerShell and navigate to this directory:

   ```powershell
   cd G:\Playing\elsba3ei-webhook-mcp
   ```

2. Run the automated setup script:

   ```powershell
   .\setup.ps1
   ```

3. Restart Claude Desktop completely (Quit from system tray, then reopen).
4. Start a new conversation in Claude to load the new tools.

---

## 🐳 Docker & MCP Installation

### Step 1: Build the Docker Image

```bash
docker build -t elsba3ei-webhook:latest .
```

### Step 2: Add to Docker MCP Profile (Docker Desktop 4.40+)

```bash
docker mcp profile server add default --server file:///G:/Playing/elsba3ei-webhook-mcp/elsba3ei-webhook-catalog.yaml
```

### Step 3: Connect to Claude Desktop

```bash
docker mcp client connect claude-desktop --global --profile default
```

### Step 4: Verify Registered Profile & Tools

```bash
docker mcp profile server ls
docker mcp tools ls | Select-String "elsba3ei"
```

---

## ⚙️ Configuring Claude Desktop Manually

Config file location: `%APPDATA%\Claude\claude_desktop_config.json`

### Direct Python Execution Mode (Recommended)

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

### Docker Container Mode

```json
{
  "mcpServers": {
    "elsba3ei-webhook": {
      "command": "docker",
      "args": [
        "--context",
        "desktop-linux",
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

## 🔧 Troubleshooting Matrix

| Symptom                                         | Root Cause                              | Fix                                                                       |
| :---------------------------------------------- | :-------------------------------------- | :------------------------------------------------------------------------ |
| `docker mcp catalog import not recognized`      | Command removed in Docker Desktop 4.40+ | Use `docker mcp profile server add default --server file://...` instead   |
| `docker mcp server enable not recognized`       | Command removed in Docker Desktop 4.40+ | Replaced by `docker mcp profile server add`                               |
| `docker mcp client connect fails: missing flag` | `--profile` is now required             | Use `docker mcp client connect claude-desktop --global --profile default` |
| Tools not appearing in Claude                   | Process uses wrong Docker context       | Add `--context desktop-linux` to docker run args                          |
| "gateway panic" / Tools vanish                  | Multi-line tool docstring               | Keep ALL `@mcp.tool()` docstrings to exactly one line                     |
| Port conflict on 4000/4040                      | Port already occupied                   | Set `WEBHOOK_PORT=4041` in environment                                    |
| Tool shows "not loaded yet"                     | Cache from previous session             | Restart Claude Desktop + start a new conversation                         |

---

## 👨‍💻 Author & Developer

Developed with ❤️ by **Ahmed E. El-Sbaei**

- 🌐 **LinkedIn**: [Ahmed E. El-Sbaei](https://www.linkedin.com/in/elsba3ei)
- 🐙 **GitHub**: [@elsba3ei](https://github.com/elsba3ei)

---

## 📄 License

Distributed under the **MIT License** — © 2026 **Ahmed E. El-Sbaei**. See [`LICENSE`](file:///G:/Playing/elsba3ei-webhook-mcp/LICENSE) for details.
