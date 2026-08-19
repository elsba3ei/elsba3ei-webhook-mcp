# =============================================================================
#  elsba3ei Webhook MCP Server Setup
#  Usage: .\setup.ps1   (run from inside the elsba3ei-webhook-mcp folder)
#  Re-runnable: safe to run multiple times.
# =============================================================================

$ErrorActionPreference = "Stop"

$ImageName   = "elsba3ei-webhook:latest"
$CatalogFile = "elsba3ei-webhook-catalog.yaml"
$ServerName  = "elsba3ei-webhook"
$ClaudeConfig = "$env:APPDATA\Claude\claude_desktop_config.json"

function Write-Step($n, $msg) { Write-Host ""; Write-Host "=== Step ${n}: $msg ===" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "  [OK]   $msg" -ForegroundColor Green  }
function Write-Fail($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red    }
function Write-Info($msg) { Write-Host "  [INFO] $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "================================================" -ForegroundColor Magenta
Write-Host "  elsba3ei Webhook MCP Server - Setup"         -ForegroundColor Magenta
Write-Host "================================================" -ForegroundColor Magenta

# 0. Pre-flight
Write-Step 0 "Pre-flight checks"
if (-not (Test-Path "Dockerfile")) {
    Write-Fail "Must be run from inside the elsba3ei-webhook-mcp folder."
    exit 1
}
Write-OK "Running from correct folder."
try { docker info *>$null; Write-OK "Docker is running." }
catch { Write-Fail "Docker is not running. Start Docker Desktop first."; exit 1 }

# 1. Build
Write-Step 1 "Build Docker image ($ImageName)"
docker build -t $ImageName .
if ($LASTEXITCODE -ne 0) { Write-Fail "Docker build failed."; exit 1 }
Write-OK "Image built."

# 2. Add server to default profile via local catalog file (new CLI)
Write-Step 2 "Add server to default profile"
$CatalogPath = "file://$((Get-Location).Path.Replace('\','/'))/$CatalogFile"
docker mcp profile server add default --server $CatalogPath 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Fail "Failed. Run manually: docker mcp profile server add default --server $CatalogPath"; exit 1 }
Write-OK "Server added to default profile."

# 3. Connect Claude Desktop (--profile is now required)
Write-Step 3 "Connect Claude Desktop"
docker mcp client connect claude-desktop --global --profile default 2>&1 | Out-Null
Write-OK "Claude Desktop connected."

# 4. Validate config
Write-Step 4 "Validate claude_desktop_config.json"
$configOK = $false
if (Test-Path $ClaudeConfig) {
    try {
        $raw = Get-Content $ClaudeConfig -Raw -Encoding UTF8
        $raw = $raw.TrimStart([char]0xFEFF)
        $parsed = $raw | ConvertFrom-Json
        if ($null -ne $parsed.mcpServers -and $null -ne $parsed.mcpServers.MCP_DOCKER) {
            Write-Host "  [SKIP] Config has MCP_DOCKER entry - not touching it." -ForegroundColor Gray
            $configOK = $true
        }
    } catch { Write-Info "Config corrupted - rewriting." }
}
if (-not $configOK) {
    $localAppData = "C:\Users\$env:USERNAME\AppData\Local"
    $jsonContent = @"
{
  "mcpServers": {
    "MCP_DOCKER": {
      "command": "docker",
      "args": ["mcp", "gateway", "run", "--profile", "default"],
      "env": {
        "LOCALAPPDATA": "$localAppData",
        "ProgramData": "C:\\ProgramData",
        "ProgramFiles": "C:\\Program Files"
      }
    }
  }
}
"@
    New-Item -ItemType Directory -Force -Path (Split-Path $ClaudeConfig) | Out-Null
    $jsonContent | Set-Content $ClaudeConfig -Encoding UTF8
    Write-OK "Config written."
}

# 5. Verify
Write-Step 5 "Verification"
Write-Host "  Docker image:" -ForegroundColor White
docker images $ImageName --format "    {{.Repository}}:{{.Tag}}  size={{.Size}}" 2>&1
Write-Host "  Profile servers:" -ForegroundColor White
docker mcp profile server ls 2>&1 | ForEach-Object { Write-Host "    $_" }
Write-Host "  Available tools:" -ForegroundColor White
docker mcp tools ls 2>&1 | Select-String "elsba3ei" | ForEach-Object { Write-Host "    $_" }

Write-Host ""
Write-Host "================================================" -ForegroundColor Magenta
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "  NEXT: Restart Claude Desktop (quit from system tray, reopen)" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Magenta
