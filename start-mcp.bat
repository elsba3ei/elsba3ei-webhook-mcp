@echo off
title 🤖 elsba3ei MCP Webhook Server [Port 4040]
color 0a
cls
echo ==============================================================================
echo   🤖 elsba3ei MCP WEBHOOK SERVER (STANDALONE TERMINAL RUNNER)
echo ==============================================================================
echo   Port:        4040
echo   Local URL:   http://127.0.0.1:4040/capture
echo   Status:      Listening for incoming webhooks, SSRF, and MCP tools...
echo.
echo   [!] TO STOP THIS SERVER: Press Ctrl+C or simply close this window.
echo ==============================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found! Run setup.ps1 first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" elsba3ei_webhook_server.py

:: Cleanup on exit
echo.
echo [i] Shutting down and cleaning up processes...
taskkill /f /im cloudflared.exe >nul 2>&1
echo [OK] Server process stopped.
pause
