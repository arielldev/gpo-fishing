@echo off
echo ========================================
echo   GPO Autofish - Easy Installation
echo ========================================
echo.

echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
echo ✓ Python found

echo.
echo [2/3] Installing required packages...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install packages
    pause
    exit /b 1
)
echo ✓ Packages installed successfully

echo.
echo [3/3] Installation complete!
echo.
echo To run GPO Autofish:
echo - Double-click "run.bat" 
echo - Or run "python z.py" as administrator
echo.
echo ========================================
echo   Installation Successful!
echo ========================================
pause