@echo off
title 🌐 elsba3ei MCP Server + Cloudflare Tunnel [Port 4040]
color 0e
cls
echo ==============================================================================
echo   🌐 elsba3ei MCP SERVER + CLOUDFLARE PUBLIC QUICK TUNNEL
echo ==============================================================================
echo   Port:          4040
echo   Public Link:   Spawning temporary HTTPS trycloudflare.com tunnel...
echo   Status:        Listening for public & local webhooks and SSRF callbacks...
echo.
echo   [!] TO STOP THIS SERVER & TUNNEL: Press Ctrl+C or simply close this window.
echo ==============================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found! Run setup.ps1 first.
    pause
    exit /b 1
)

set AUTO_START_TUNNEL=true
".venv\Scripts\python.exe" elsba3ei_webhook_server.py

:: Cleanup on exit
echo.
echo [i] Shutting down and cleaning up processes...
taskkill /f /im cloudflared.exe >nul 2>&1
echo [OK] Server and tunnel stopped.
pause
