=============================================================================
 elsba3ei WEBHOOK MCP SERVER - DOCUMENTATION & GUIDE
=============================================================================

High-performance local & public Webhook Inspector and Burp Suite Collaborator
alternative for testing SSRF, APIs, and Out-Of-Band (OOB) interactions with
Cloudflare Quick Tunnel support, dynamic mock responses, live request capture,
and callback polling.

-----------------------------------------------------------------------------
1. OVERVIEW & CAPABILITIES
-----------------------------------------------------------------------------
The elsba3ei-webhook MCP server allows Claude Desktop and AI agents to:
- Instantly spin up local (http://127.0.0.1:4040/capture) and public Cloudflare
  Quick Tunnels (https://*.trycloudflare.com/capture) with no account needed.
- Inspect incoming HTTP/HTTPS requests (method, headers, query, client IP,
  JSON, form, raw text, or binary hex dump).
- Dynamically mock responses with custom status codes, content-types,
  headers, and simulated response latency.
- Poll & block waiting for out-of-band SSRF / webhook callbacks (wait_for_request).
- Replay and forge custom HTTP requests (replay_request).

-----------------------------------------------------------------------------
2. AVAILABLE MCP TOOLS
-----------------------------------------------------------------------------
1. get_webhook_urls
   - Returns all available localhost, LAN, and public Cloudflare capture URLs.
   - Example: get_webhook_urls()

2. start_tunnel
   - Launches a temporary Cloudflare Quick Tunnel to expose port 4040 publicly.
   - Example: start_tunnel(port="4040")

3. stop_tunnel
   - Terminates the Cloudflare tunnel subprocess.
   - Example: stop_tunnel()

4. get_tunnel_status
   - Returns the active tunnel URL, status, and uptime.
   - Example: get_tunnel_status()

5. list_requests
   - Summarizes captured requests (limit, method filter, path filter).
   - Example: list_requests(limit="20", method="POST", path_filter="/ssrf")

6. get_request_details
   - Fetches full headers, parsed/raw body, and client IP of a request ID.
   - Example: get_request_details(request_id="<uuid>")

7. wait_for_request
   - Polls until an incoming request matches path, method, or body within a timeout.
   - Example: wait_for_request(timeout_seconds="30", path_contains="oob-token")

8. configure_mock_response
   - Sets dynamic HTTP status, content-type, body, delay, and custom headers.
   - Example: configure_mock_response(status_code="500", response_body="Internal Error")

9. reset_mock_response
   - Resets mock engine back to default 200 OK JSON.
   - Example: reset_mock_response()

10. clear_requests
    - Purges the in-memory ring buffer of captured requests.
    - Example: clear_requests()

11. delete_request
    - Removes a single request record by ID.
    - Example: delete_request(request_id="<uuid>")

12. replay_request
    - Sends an HTTP request to any target URL and captures the response.
    - Example: replay_request(target_url="https://httpbin.org/get", method="GET")

13. get_server_status
    - Returns server health, active port, uptime, and captured request counts.
    - Example: get_server_status()

-----------------------------------------------------------------------------
3. QUICK START SETUP (WINDOWS POWERSHELL)
-----------------------------------------------------------------------------
1. Open PowerShell and navigate to the project directory:
   cd G:\Playing\elsba3ei-webhook-mcp

2. Run the automated setup script:
   .\setup.ps1

3. Restart Claude Desktop completely (Quit from system tray, then reopen).
4. Start a new conversation in Claude to load the new tools.

-----------------------------------------------------------------------------
4. MANUAL DOCKER & MCP INSTALLATION
-----------------------------------------------------------------------------
Step 1: Build the Docker Image
   docker build -t elsba3ei-webhook:latest .

Step 2: Add to Docker MCP Profile (Docker Desktop 4.40+)
   docker mcp profile server add default --server file:///G:/Playing/elsba3ei-webhook-mcp/elsba3ei-webhook-catalog.yaml

Step 3: Connect to Claude Desktop
   docker mcp client connect claude-desktop --global --profile default

Step 4: Verify Registered Profile & Tools
   docker mcp profile server ls
   docker mcp tools ls | Select-String "elsba3ei"

-----------------------------------------------------------------------------
5. CONFIGURING CLAUDE DESKTOP MANUALLY
-----------------------------------------------------------------------------
Config file location:
- Windows: %APPDATA%\Claude\claude_desktop_config.json

Option A — Gateway Mode:
{
  "mcpServers": {
    "MCP_DOCKER": {
      "command": "docker",
      "args": ["mcp", "gateway", "run", "--profile", "default"],
      "env": {
        "LOCALAPPDATA": "C:\\Users\\USERNAME\\AppData\\Local",
        "ProgramData": "C:\\ProgramData",
        "ProgramFiles": "C:\\Program Files"
      }
    }
  }
}

Option B — Named Server Direct Mode:
{
  "mcpServers": {
    "elsba3ei-webhook": {
      "command": "docker",
      "args": ["--context", "desktop-linux", "run", "-i", "--rm", "-p", "4000:4000", "elsba3ei-webhook:latest"]
    }
  }
}

-----------------------------------------------------------------------------
6. TROUBLESHOOTING REFERENCE
-----------------------------------------------------------------------------
| Symptom                                          | Root Cause                                                     | Fix                                                                                        |
| ------------------------------------------------ | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| docker mcp catalog import not recognized         | Command removed in Docker Desktop 4.40+                        | Use docker mcp profile server add default --server file://... instead                      |
| docker mcp server enable not recognized          | Command removed in Docker Desktop 4.40+                        | Replaced by docker mcp profile server add                                                  |
| docker mcp client connect fails: missing flag    | --profile is now required                                      | Use docker mcp client connect claude-desktop --global --profile default                    |
| Tools not appearing — server added but invisible | Docker Desktop child process uses wrong Docker context         | Add --context desktop-linux to docker run args in claude_desktop_config.json               |
| Tools named mcp__MCP_DOCKER__* not mcp__X__*     | Server is routed through the gateway, not a direct entry       | Add a named entry to claude_desktop_config.json (Option B); remove from gateway profile    |
| "gateway panic" — tools vanish                   | Multi-line tool docstring                                      | Keep ALL @mcp.tool() docstrings to exactly one line                                        |
| Config corrupted/emptied                         | PowerShell ConvertTo-Json mangles JSON arrays                  | Use heredoc strings; only write if missing/corrupted                                       |
| Port conflict on 4000                            | Host port 4000 already occupied                                | Change port or set WEBHOOK_PORT environment variable                                        |
| Tool shows "not loaded yet" in Claude            | New tools not picked up in current session                     | Restart Claude Desktop + start a new conversation                                          |

=============================================================================
