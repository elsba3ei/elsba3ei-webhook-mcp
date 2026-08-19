@echo off
title 🛑 Stop All elsba3ei Webhook & MCP Servers
color 0c
cls
echo ==============================================================================
echo   🛑 STOPPING ALL elsba3ei SERVERS (Ports 4000 & 4040)
echo ==============================================================================
echo.

powershell -Command "
`$ports = @(4000, 4040)
foreach (`$p in `$ports) {
    `$conns = Get-NetTCPConnection -LocalPort `$p -ErrorAction SilentlyContinue
    if (`$conns) {
        `$pids = `$conns | Select-Object -ExpandProperty OwningProcess -Unique
        foreach (`$pidToKill in `$pids) {
            try {
                Stop-Process -Id `$pidToKill -Force -ErrorAction SilentlyContinue
                Write-Host \"[OK] Stopped process `$pidToKill on port `$p\" -ForegroundColor Green
            } catch {
                Write-Host \"[!] Could not stop PID `$pidToKill on port `$p\" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host \"[i] Port `$p is already free.\" -ForegroundColor Gray
    }
}
"

echo.
echo ==============================================================================
echo   All ports (4000 & 4040) are now free!
echo ==============================================================================
echo.
pause
