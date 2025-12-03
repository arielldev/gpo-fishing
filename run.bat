@echo off
setlocal enabledelayedexpansion
title GPO Autofish - Starting...
cd /d "%~dp0"

echo ========================================
echo   GPO Autofish - Loading...
echo ========================================
echo.

REM Look for Python installations in order of preference
set PYTHON_EXE=
set PYTHON_FOUND=0

echo Looking for Python 3.13 installation...
if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe" (
    set PYTHON_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe
    set PYTHON_FOUND=1
    echo Found Python 3.13 at: !PYTHON_EXE!
    goto python_found
)

echo Python 3.13 not found, looking for Python 3.12...
if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe" (
    set PYTHON_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe
    set PYTHON_FOUND=1
    echo Found Python 3.12 at: !PYTHON_EXE!
    goto python_found
)

echo No specific Python version found, using py launcher...
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_EXE=py -3
    set PYTHON_FOUND=1
    echo Using py launcher for Python 3
    goto python_found
)

echo ERROR: No Python installation found
echo Please install Python 3.12 or 3.13 from https://python.org
echo Python 3.14+ is not supported due to package compatibility issues
pause
exit /b 1

:python_found
echo.

echo Using Python: !PYTHON_EXE!
!PYTHON_EXE! --version

REM Check if virtual environment exists and activate it
if exist ".venv\Scripts\activate.bat" (
    echo.
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    echo ✅ Virtual environment activated
) else (
    echo.
    echo ⚠️ Virtual environment not found - using system Python
)

echo.
echo Starting GPO Autofish...
echo ========================================
echo.

REM Start Python minimized (no visible window)
start /MIN "" !PYTHON_EXE! src/main.py

echo ✅ Macro started successfully!
echo This window will close in 3 seconds...
timeout /t 3 /nobreak >nul
exit