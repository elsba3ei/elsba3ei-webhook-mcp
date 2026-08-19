#!/usr/bin/env python3
"""
elsba3ei Webhook MCP Server
High-performance local & public Webhook Inspector and Burp Suite Collaborator alternative
for testing SSRF, APIs, and Out-Of-Band (OOB) interactions.
"""

import os
import re
import sys
import json
import time
import uuid
import socket
import base64
import atexit
import asyncio
import logging
import warnings
import threading
import subprocess
from datetime import datetime

# Filter out library warnings so stderr only carries intentional logs
warnings.filterwarnings("ignore")

import httpx
from aiohttp import web
from mcp.server.fastmcp import FastMCP

# Logging to stderr ONLY — stdout is the MCP JSON-RPC channel
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("elsba3ei-webhook-server")

# Initialize FastMCP — NO prompt= parameter
mcp = FastMCP("elsba3ei-webhook")

# ── CONFIGURATION & CONSTANTS ────────────────────────────────────────────────
DEFAULT_TIMEOUT = int(os.environ.get("TOOL_TIMEOUT", "300"))
WEBHOOK_PORT = int(os.environ.get("WEBHOOK_PORT", "4040"))
AUTO_START_TUNNEL = os.environ.get("AUTO_START_TUNNEL", "false").lower() in ("true", "1", "yes")
MAX_STORED_REQUESTS = 1000

# ── STATE STORAGE & THREAD SAFETY ────────────────────────────────────────────
state_lock = threading.Lock()
captured_requests = []
server_start_time = time.time()

mock_config = {
    "statusCode": 200,
    "contentType": "application/json",
    "responseBody": json.dumps({"status": "ok", "message": "Captured by elsba3ei Webhook"}, indent=2),
    "customHeaders": {
        "Server": "elsba3ei-Webhook/1.0",
        "X-Powered-By": "elsba3ei-Inspector"
    },
    "delayMs": 0,
    "autoCors": True
}

tunnel_state = {
    "process": None,
    "url": None,
    "status": "stopped",
    "started_at": None,
    "error": None
}

# ── INPUT SANITIZATION HELPERS ───────────────────────────────────────────────

def sanitize_url(url: str) -> str:
    """Require http:// or https:// prefix with URL-safe characters."""
    u = url.strip()
    if not u:
        raise ValueError("URL must not be empty.")
    if not re.match(r'^https?://[a-zA-Z0-9\-_.:%#?&=/@~+]+', u):
        raise ValueError("URL must begin with http:// or https:// and contain valid URL characters.")
    return u

def sanitize_int(val: str, default: int = 0, min_val: int = 0, max_val: int = 65535) -> int:
    """Safely parse integer within specified bounds."""
    if not val or not str(val).strip():
        return default
    try:
        n = int(str(val).strip())
        return max(min_val, min(n, max_val))
    except (ValueError, TypeError):
        raise ValueError(f"Invalid integer: {val}")

def sanitize_method(method: str) -> str:
    """Safely sanitize HTTP method token."""
    m = method.strip().upper()
    if not m:
        return ""
    if not re.match(r'^[A-Z]{3,10}$', m):
        raise ValueError(f"Invalid HTTP method: {method}")
    return m

def sanitize_id(req_id: str) -> str:
    """Sanitize alphanumeric/UUID identifier."""
    i = req_id.strip()
    if not i:
        return ""
    if not re.match(r'^[a-zA-Z0-9\-_]{1,64}$', i):
        raise ValueError(f"Invalid ID format: {req_id}")
    return i

# ── NETWORK & SYSTEM HELPERS ─────────────────────────────────────────────────

def get_local_ips():
    """Discover all non-loopback IPv4 addresses on local interfaces."""
    ip_list = []
    try:
        host_name = socket.gethostname()
        for ip in socket.gethostbyname_ex(host_name)[2]:
            if not ip.startswith("127.") and ip not in ip_list:
                ip_list.append(ip)
    except Exception:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        routed_ip = s.getsockname()[0]
        s.close()
        if routed_ip and not routed_ip.startswith("127.") and routed_ip not in ip_list:
            ip_list.append(routed_ip)
    except Exception:
        pass

    return ip_list

def resolve_client_ip(headers, peer_ip: str) -> str:
    """Resolve true client IP using standard reverse-proxy headers."""
    forwarded = headers.get("x-forwarded-for", "")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            return parts[0]
    return (
        headers.get("cf-connecting-ip")
        or headers.get("x-real-ip")
        or headers.get("true-client-ip")
        or peer_ip
        or "127.0.0.1"
    )

def parse_body_payload(raw_bytes: bytes, content_type: str):
    """Analyze and parse incoming body payload into JSON, form, text, or binary hex."""
    size = len(raw_bytes)
    if size == 0:
        return {"raw": "", "parsed": None, "type": "empty", "size": 0}

    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        hex_dump = " ".join(f"{b:02x}" for b in raw_bytes[:1024])
        return {
            "raw": base64.b64encode(raw_bytes).decode("ascii"),
            "hex": hex_dump,
            "parsed": None,
            "type": "binary",
            "size": size
        }

    ct = content_type.lower()
    if "application/json" in ct:
        try:
            return {"raw": raw_text, "parsed": json.loads(raw_text), "type": "json", "size": size}
        except Exception:
            return {"raw": raw_text, "parsed": None, "type": "text", "size": size}

    if "application/x-www-form-urlencoded" in ct:
        try:
            import urllib.parse
            parsed_form = urllib.parse.parse_qs(raw_text)
            return {"raw": raw_text, "parsed": parsed_form, "type": "form", "size": size}
        except Exception:
            return {"raw": raw_text, "parsed": None, "type": "text", "size": size}

    try:
        json_obj = json.loads(raw_text)
        return {"raw": raw_text, "parsed": json_obj, "type": "json", "size": size}
    except Exception:
        return {"raw": raw_text, "parsed": None, "type": "text", "size": size}

# ── CLOUDFLARE TUNNEL SUBPROCESS MANAGEMENT ──────────────────────────────────

def _read_tunnel_output(process):
    """Background reader for cloudflared output to detect public trycloudflare.com URL."""
    pattern = re.compile(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
    while True:
        line = process.stderr.readline()
        if not line and process.poll() is not None:
            break
        if line:
            decoded = line.strip()
            match = pattern.search(decoded)
            if match and not tunnel_state["url"]:
                with state_lock:
                    tunnel_state["url"] = match.group(0)
                    tunnel_state["status"] = "running"
                    tunnel_state["started_at"] = time.time()
                logger.info(f"Cloudflare Tunnel ACTIVE: {tunnel_state['url']}")

def start_tunnel_sync(port: int) -> dict:
    """Start cloudflared quick tunnel subprocess synchronously."""
    global tunnel_state
    with state_lock:
        if tunnel_state["status"] == "running" and tunnel_state["url"]:
            return {
                "status": "running",
                "tunnel_url": tunnel_state["url"],
                "capture_url": tunnel_state["url"],
                "message": "Tunnel is already running."
            }

        tunnel_state["status"] = "starting"
        tunnel_state["error"] = None
        tunnel_state["url"] = None

    try:
        proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        with state_lock:
            tunnel_state["process"] = proc

        t = threading.Thread(target=_read_tunnel_output, args=(proc,), daemon=True)
        t.start()

        # Wait up to 20 seconds for URL detection
        for _ in range(40):
            time.sleep(0.5)
            with state_lock:
                if tunnel_state["url"]:
                    return {
                        "status": "running",
                        "tunnel_url": tunnel_state["url"],
                        "capture_url": tunnel_state["url"],
                        "message": "Cloudflare Quick Tunnel established successfully."
                    }
                if proc.poll() is not None:
                    break

        if proc.poll() is not None:
            err_output = proc.stderr.read()
            with state_lock:
                tunnel_state["status"] = "error"
                tunnel_state["error"] = err_output or "Process terminated prematurely."
                tunnel_state["process"] = None
            return {"status": "error", "error": tunnel_state["error"]}

        # Timed out waiting for URL
        with state_lock:
            if not tunnel_state["url"]:
                tunnel_state["status"] = "starting"
        return {
            "status": "starting",
            "message": "Tunnel process spawned, URL negotiation in progress. Check status in a moment."
        }
    except FileNotFoundError:
        with state_lock:
            tunnel_state["status"] = "error"
            tunnel_state["error"] = "cloudflared binary not found in PATH."
            tunnel_state["process"] = None
        return {"status": "error", "error": "cloudflared binary not found in PATH."}
    except Exception as e:
        with state_lock:
            tunnel_state["status"] = "error"
            tunnel_state["error"] = str(e)
            tunnel_state["process"] = None
        return {"status": "error", "error": str(e)}

def stop_tunnel_sync() -> dict:
    """Stop active cloudflared tunnel subprocess safely."""
    global tunnel_state
    with state_lock:
        proc = tunnel_state["process"]
        if proc:
            try:
                if os.name == 'nt':
                    try:
                        subprocess.run(["taskkill", "/pid", str(proc.pid), "/f", "/t"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as e:
                logger.error(f"Error stopping cloudflared: {e}")
        tunnel_state["process"] = None
        tunnel_state["url"] = None
        tunnel_state["status"] = "stopped"
        tunnel_state["started_at"] = None
        tunnel_state["error"] = None
    return {"status": "stopped", "message": "Cloudflare Tunnel stopped successfully."}

atexit.register(stop_tunnel_sync)

try:
    import signal
    def _sig_cleanup(signum, frame):
        stop_tunnel_sync()
        sys.exit(0)
    signal.signal(signal.SIGINT, _sig_cleanup)
    signal.signal(signal.SIGTERM, _sig_cleanup)
except Exception:
    pass

# ── AIOHTTP BACKGROUND WEBHOOK CAPTURE SERVER ────────────────────────────────

async def http_request_handler(request: web.Request) -> web.Response:
    """Handle and capture all incoming HTTP requests on any path and method."""
    pathname = request.path

    # Ignore browser / crawler noise
    if pathname in ("/favicon.ico", "/apple-touch-icon.png", "/apple-touch-icon-precomposed.png", "/browserconfig.xml"):
        return web.Response(status=204)
    if pathname == "/robots.txt":
        return web.Response(text="User-agent: *\nDisallow: /", content_type="text/plain")

    # Serve built-in status API if queried directly
    if pathname == "/api/status" and request.method == "GET":
        with state_lock:
            return web.json_response({
                "status": "running",
                "uptime": time.time() - server_start_time,
                "captured": len(captured_requests),
                "tunnel": tunnel_state["status"],
                "tunnel_url": tunnel_state["url"]
            })

    # Read body
    try:
        raw_body = await request.read()
    except Exception:
        raw_body = b""

    headers_dict = dict(request.headers)
    client_ip = resolve_client_ip(headers_dict, request.remote or "127.0.0.1")
    content_type = headers_dict.get("content-type", "")
    parsed_body = parse_body_payload(raw_body, content_type)

    query_params = dict(request.query)
    req_id = str(uuid.uuid4())
    now = datetime.utcnow()

    with state_lock:
        current_mock = dict(mock_config)

    captured_record = {
        "id": req_id,
        "timestamp": now.isoformat() + "Z",
        "timestampLocal": now.strftime("%H:%M:%S"),
        "method": request.method,
        "url": str(request.url),
        "path": pathname,
        "protocol": headers_dict.get("x-forwarded-proto", request.scheme),
        "httpVersion": f"{request.version.major}.{request.version.minor}",
        "clientIP": client_ip,
        "headers": headers_dict,
        "rawHeaders": [f"{k}: {v}" for k, v in request.headers.items()],
        "query": query_params,
        "rawQuery": request.query_string,
        "body": parsed_body,
        "size": len(raw_body),
        "responseSent": {
            "statusCode": current_mock["statusCode"],
            "contentType": current_mock["contentType"],
            "customHeaders": current_mock["customHeaders"],
            "body": current_mock["responseBody"]
        }
    }

    with state_lock:
        captured_requests.insert(0, captured_record)
        if len(captured_requests) > MAX_STORED_REQUESTS:
            captured_requests.pop()

    logger.info(f"[+] INCOMING {request.method} {pathname} from {client_ip} ({len(raw_body)} bytes)")

    # Apply simulated delay if configured
    if current_mock["delayMs"] > 0:
        await asyncio.sleep(current_mock["delayMs"] / 1000.0)

    # Build response headers
    response_headers = {
        "Content-Type": current_mock["contentType"],
        **current_mock["customHeaders"]
    }
    if current_mock.get("autoCors", True):
        response_headers.update({
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD, TRACE",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Expose-Headers": "*",
            "Access-Control-Max-Age": "86400"
        })

    resp_body_str = current_mock["responseBody"]
    return web.Response(
        body=resp_body_str.encode("utf-8", errors="replace"),
        status=current_mock["statusCode"],
        headers=response_headers
    )

def _run_aiohttp_server(port: int):
    """Run aiohttp capture server in a dedicated background daemon thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = web.Application(client_max_size=50 * 1024 * 1024)
    app.router.add_route('*', '/{path:.*}', http_request_handler)

    async def start():
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"elsba3ei Webhook background HTTP listener listening on 0.0.0.0:{port}")
        while True:
            await asyncio.sleep(3600)

    try:
        loop.run_until_complete(start())
    except Exception as e:
        logger.error(f"HTTP Server failed: {e}", exc_info=True)

# Start background HTTP server thread immediately on import/startup
_server_thread = threading.Thread(target=_run_aiohttp_server, args=(WEBHOOK_PORT,), daemon=True)
_server_thread.start()

if AUTO_START_TUNNEL:
    logger.info("AUTO_START_TUNNEL is active. Establishing Cloudflare Quick Tunnel...")
    start_tunnel_sync(WEBHOOK_PORT)

# ── MCP TOOLS ────────────────────────────────────────────────────────────────
# RULE: Every docstring must be EXACTLY ONE LINE. Multi-line = gateway panic.
# RULE: Every parameter must default to "" (empty string), never None.
# RULE: Every tool must return str.

@mcp.tool()
async def get_webhook_urls(dummy: str = "") -> str:
    """Get all available local, LAN, and public Cloudflare tunnel webhook capture URLs."""
    local_ips = get_local_ips()
    with state_lock:
        c_tunnel = tunnel_state["url"]
        t_status = tunnel_state["status"]

    lan_urls = [f"http://{ip}:{WEBHOOK_PORT}/capture" for ip in local_ips]
    public_url = c_tunnel if c_tunnel else None

    result = {
        "status": "ok",
        "webhook_port": WEBHOOK_PORT,
        "localhost_url": f"http://127.0.0.1:{WEBHOOK_PORT}/capture",
        "lan_urls": lan_urls,
        "public_cloudflare_url": public_url,
        "tunnel_status": t_status,
        "supported_paths": "Direct Root (/) or any custom subpath (e.g. /ssrf, /api/webhook, /oob, /payload)",
        "supported_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
    }
    return json.dumps(result, indent=2)

@mcp.tool()
async def start_tunnel(port: str = "4040") -> str:
    """Start a temporary Cloudflare Quick Tunnel to expose the webhook server to the public Internet."""
    p = sanitize_int(port, default=WEBHOOK_PORT, min_val=1, max_val=65535)
    res = start_tunnel_sync(p)
    return json.dumps(res, indent=2)

@mcp.tool()
async def stop_tunnel(dummy: str = "") -> str:
    """Stop the running Cloudflare Quick Tunnel and deactivate public HTTPS access."""
    res = stop_tunnel_sync()
    return json.dumps(res, indent=2)

@mcp.tool()
async def get_tunnel_status(dummy: str = "") -> str:
    """Check if the Cloudflare tunnel is active, starting, or stopped, and return the public URL."""
    with state_lock:
        uptime = (time.time() - tunnel_state["started_at"]) if tunnel_state.get("started_at") else 0
        res = {
            "status": tunnel_state["status"],
            "tunnel_url": tunnel_state["url"],
            "public_webhook_url": tunnel_state['url'] if tunnel_state['url'] else None,
            "uptime_seconds": round(uptime, 2) if uptime else 0,
            "error": tunnel_state["error"]
        }
    return json.dumps(res, indent=2)

@mcp.tool()
async def list_requests(limit: str = "20", method: str = "", path_filter: str = "") -> str:
    """List captured HTTP webhook requests with summary metadata."""
    lim = sanitize_int(limit, default=20, min_val=1, max_val=1000)
    meth = sanitize_method(method)
    p_filter = path_filter.strip().lower()

    with state_lock:
        filtered = []
        for req in captured_requests:
            if meth and req.get("method") != meth:
                continue
            if p_filter and p_filter not in req.get("path", "").lower() and p_filter not in req.get("url", "").lower():
                continue
            summary = {
                "id": req.get("id"),
                "timestamp": req.get("timestamp"),
                "method": req.get("method"),
                "path": req.get("path"),
                "client_ip": req.get("clientIP"),
                "size_bytes": req.get("size"),
                "body_type": req.get("body", {}).get("type", "unknown")
            }
            filtered.append(summary)
            if len(filtered) >= lim:
                break

    return json.dumps({
        "total_captured": len(captured_requests),
        "returned_count": len(filtered),
        "requests": filtered
    }, indent=2)

@mcp.tool()
async def get_request_details(request_id: str = "") -> str:
    """Get complete details of a captured request by ID."""
    rid = sanitize_id(request_id)
    if not rid:
        return json.dumps({"error": "request_id parameter is required"}, indent=2)

    with state_lock:
        for req in captured_requests:
            if req.get("id") == rid:
                return json.dumps(req, indent=2)

    with state_lock:
        recent_ids = [r.get("id") for r in captured_requests[:5]]
    return json.dumps({
        "error": f"Request ID '{rid}' not found.",
        "recent_available_ids": recent_ids
    }, indent=2)

@mcp.tool()
async def wait_for_request(timeout_seconds: str = "15", path_contains: str = "", method: str = "", match_body: str = "") -> str:
    """Wait and poll for an incoming OOB callback or SSRF request matching criteria within a timeout."""
    timeout = sanitize_int(timeout_seconds, default=15, min_val=1, max_val=300)
    meth = sanitize_method(method)
    path_pat = path_contains.strip().lower()
    body_pat = match_body.strip().lower()

    start_wait_time = time.time()
    poll_interval = 0.25

    while (time.time() - start_wait_time) < timeout:
        with state_lock:
            for req in captured_requests:
                # Check if captured during or slightly before the wait window
                req_ts = req.get("timestamp", "")
                if meth and req.get("method") != meth:
                    continue
                if path_pat and path_pat not in req.get("path", "").lower() and path_pat not in req.get("url", "").lower():
                    continue
                if body_pat:
                    raw_b = str(req.get("body", {}).get("raw", "")).lower()
                    if body_pat not in raw_b:
                        continue
                elapsed = round(time.time() - start_wait_time, 2)
                return json.dumps({
                    "status": "captured",
                    "elapsed_seconds": elapsed,
                    "matched_request": req
                }, indent=2)

        await asyncio.sleep(poll_interval)

    elapsed_total = round(time.time() - start_wait_time, 2)
    return json.dumps({
        "status": "timeout",
        "message": f"No matching callback received within {elapsed_total}s.",
        "filters": {
            "timeout_seconds": timeout,
            "path_contains": path_contains,
            "method": method,
            "match_body": match_body
        }
    }, indent=2)

@mcp.tool()
async def configure_mock_response(status_code: str = "200", content_type: str = "application/json", response_body: str = "", delay_ms: str = "0", custom_headers_json: str = "{}") -> str:
    """Configure the HTTP response returned to incoming webhook and SSRF callers."""
    code = sanitize_int(status_code, default=200, min_val=100, max_val=599)
    delay = sanitize_int(delay_ms, default=0, min_val=0, max_val=60000)
    ct = content_type.strip() or "application/json"

    custom_headers = {}
    if custom_headers_json.strip():
        try:
            parsed = json.loads(custom_headers_json)
            if isinstance(parsed, dict):
                custom_headers = {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            return json.dumps({"error": "custom_headers_json must be a valid JSON object string"}, indent=2)

    body_val = response_body
    if not body_val:
        if "application/json" in ct:
            body_val = json.dumps({"status": "ok", "mock_status": code}, indent=2)
        else:
            body_val = f"OK {code}"

    with state_lock:
        mock_config["statusCode"] = code
        mock_config["contentType"] = ct
        mock_config["responseBody"] = body_val
        mock_config["delayMs"] = delay
        mock_config["customHeaders"] = custom_headers
        current = dict(mock_config)

    return json.dumps({
        "status": "success",
        "message": "Mock response updated successfully",
        "active_config": current
    }, indent=2)

@mcp.tool()
async def reset_mock_response(dummy: str = "") -> str:
    """Reset mock response settings back to default 200 OK JSON."""
    with state_lock:
        mock_config["statusCode"] = 200
        mock_config["contentType"] = "application/json"
        mock_config["responseBody"] = json.dumps({"status": "ok", "message": "Captured by elsba3ei Webhook"}, indent=2)
        mock_config["customHeaders"] = {
            "Server": "elsba3ei-Webhook/1.0",
            "X-Powered-By": "elsba3ei-Inspector"
        }
        mock_config["delayMs"] = 0
        mock_config["autoCors"] = True
        current = dict(mock_config)

    return json.dumps({
        "status": "success",
        "message": "Mock response reset to defaults",
        "active_config": current
    }, indent=2)

@mcp.tool()
async def clear_requests(dummy: str = "") -> str:
    """Clear all captured requests from memory."""
    with state_lock:
        cleared_count = len(captured_requests)
        captured_requests.clear()

    return json.dumps({
        "status": "success",
        "message": f"Cleared {cleared_count} captured requests from memory.",
        "remaining_count": 0
    }, indent=2)

@mcp.tool()
async def delete_request(request_id: str = "") -> str:
    """Delete a specific captured request by ID."""
    rid = sanitize_id(request_id)
    if not rid:
        return json.dumps({"error": "request_id parameter is required"}, indent=2)

    with state_lock:
        idx = next((i for i, r in enumerate(captured_requests) if r.get("id") == rid), None)
        if idx is not None:
            deleted = captured_requests.pop(idx)
            return json.dumps({
                "status": "success",
                "message": f"Deleted request {rid}",
                "deleted_summary": {
                    "id": deleted.get("id"),
                    "method": deleted.get("method"),
                    "path": deleted.get("path")
                }
            }, indent=2)

    return json.dumps({"error": f"Request ID '{rid}' not found"}, indent=2)

@mcp.tool()
async def replay_request(target_url: str = "", method: str = "GET", headers_json: str = "{}", body: str = "") -> str:
    """Replay a captured request or send a customized HTTP request to a target URL."""
    try:
        t_url = sanitize_url(target_url)
    except ValueError as ve:
        return json.dumps({"error": str(ve)}, indent=2)

    m = sanitize_method(method) or "GET"

    headers = {}
    if headers_json.strip():
        try:
            parsed = json.loads(headers_json)
            if isinstance(parsed, dict):
                headers = {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            return json.dumps({"error": "headers_json must be a valid JSON object string"}, indent=2)

    start_t = time.time()
    try:
        async with httpx.AsyncClient(verify=False, follow_redirects=True, timeout=float(DEFAULT_TIMEOUT)) as client:
            resp = await client.request(
                method=m,
                url=t_url,
                headers=headers,
                content=body.encode("utf-8") if body else None
            )
            latency_ms = round((time.time() - start_t) * 1000, 2)

            resp_text = resp.text
            if len(resp_text) > 50000:
                resp_text = resp_text[:50000] + "... [TRUNCATED]"

            return json.dumps({
                "status_code": resp.status_code,
                "reason_phrase": resp.reason_phrase,
                "latency_ms": latency_ms,
                "headers": dict(resp.headers),
                "body": resp_text
            }, indent=2)
    except Exception as e:
        latency_ms = round((time.time() - start_t) * 1000, 2)
        return json.dumps({
            "error": str(e),
            "latency_ms": latency_ms,
            "target_url": t_url,
            "method": m
        }, indent=2)

@mcp.tool()
async def get_server_status(dummy: str = "") -> str:
    """Get server health, active port, uptime, captured request count, and network interfaces."""
    with state_lock:
        req_count = len(captured_requests)
        t_status = tunnel_state["status"]
        t_url = tunnel_state["url"]
        m_conf = dict(mock_config)

    uptime_sec = round(time.time() - server_start_time, 2)
    local_ips = get_local_ips()

    result = {
        "status": "healthy",
        "service": "elsba3ei Webhook & SSRF Inspector",
        "webhook_port": WEBHOOK_PORT,
        "uptime_seconds": uptime_sec,
        "captured_requests_count": req_count,
        "local_network_ips": local_ips,
        "cloudflare_tunnel": {
            "status": t_status,
            "url": t_url,
            "capture_url": t_url if t_url else None
        },
        "active_mock_response": {
            "status_code": m_conf["statusCode"],
            "content_type": m_conf["contentType"],
            "delay_ms": m_conf["delayMs"]
        }
    }
    return json.dumps(result, indent=2)

# ── SERVER STARTUP ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Starting elsba3ei Webhook MCP Server...")
    try:
        # Run FastMCP stdio interface
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
