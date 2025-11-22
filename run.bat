@echo off
title GPO Autofish - Open Source

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running as Administrator - Starting GPO Autofish...
    python z.py
) else (
    echo This application requires Administrator privileges for hotkey support.
    echo Restarting as Administrator...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
)
pause