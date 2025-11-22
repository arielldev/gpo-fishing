@echo off

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    REM Run Python script without console window
    pythonw z.py
) else (
    REM Restart as administrator silently
    powershell -WindowStyle Hidden -Command "Start-Process '%~f0' -Verb RunAs -WindowStyle Hidden"
)