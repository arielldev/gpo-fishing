@echo off
REM Start Python script without console window and exit CMD
cd /d "%~dp0"
start "" pythonw src/main.py
exit