@echo off
title GPO Autofish - Development Mode
color 0A
cd /d "%~dp0"

echo ========================================
echo   GPO Autofish - Development Mode
echo ========================================
echo.
echo This mode shows console output for debugging
echo.
echo Default Hotkeys:
echo   F1 - Start/Pause/Resume Fishing
echo   F2 - Toggle Overlay
echo   F3 - Exit Program
echo   F4 - Toggle System Tray
echo.
echo Note: If hotkeys don't work, try running as Administrator
echo.
echo Starting GPO Autofish...
echo ========================================
echo.

python src/main.py

echo.
echo ========================================
echo Program ended. Press any key to close...
pause >nul