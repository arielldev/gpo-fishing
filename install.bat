@echo off
echo ========================================
echo   GPO Autofish - Easy Installation
echo ========================================
echo.

echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python %PYTHON_VERSION% found

echo.
echo [2/4] Upgrading pip to latest version...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo WARNING: Could not upgrade pip, continuing anyway...
)

echo.
echo [3/4] Installing required packages...
echo Installing core dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install packages
    echo.
    echo Trying alternative installation method...
    pip install keyboard pynput pywin32 mss numpy pillow pystray requests
    if errorlevel 1 (
        echo ERROR: Installation failed completely
        echo.
        echo Please try running as administrator or check your internet connection
        pause
        exit /b 1
    )
)
echo ✓ Packages installed successfully

echo.
echo [4/4] Verifying installation...
python -c "import keyboard, pynput, win32api, mss, numpy; print('✓ Core modules verified')" 2>nul
if errorlevel 1 (
    echo WARNING: Some core modules may not be properly installed
    echo The program may still work, but some features might be limited
)

python -c "import pystray, requests; print('✓ Optional modules verified')" 2>nul
if errorlevel 1 (
    echo NOTE: Optional modules (system tray, webhooks) may be limited
)

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo To run GPO Autofish:
echo   • Double-click "run.bat" (recommended)
echo   • Or run "python z.py" in command prompt
echo.
echo Features available:
echo   ✓ Auto-fishing with PD controller
echo   ✓ Auto-purchase system
echo   ✓ Discord webhook notifications
echo   ✓ System tray support
echo   ✓ Auto-recovery system
echo   ✓ Pause/Resume functionality
echo.
echo Press any key to exit...
pause >nul