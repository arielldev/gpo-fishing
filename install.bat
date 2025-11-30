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
python -m pip install --upgrade pip >nul 2>&1
if errorlevel 1 (
    echo WARNING: Could not upgrade pip, continuing anyway...
) else (
    echo ✓ Pip upgraded successfully
)

echo.
echo [3/4] Installing required packages...
echo Installing essential dependencies directly...
echo This may take a few minutes...

echo Installing core packages...
python -m pip install keyboard==0.13.5 --no-warn-script-location
python -m pip install pynput==1.8.1 --no-warn-script-location
python -m pip install mss==10.1.0 --no-warn-script-location
python -m pip install numpy --no-warn-script-location
python -m pip install pillow --no-warn-script-location
python -m pip install requests --no-warn-script-location
python -m pip install pywin32 --no-warn-script-location
python -m pip install pystray --no-warn-script-location

echo Installing lightweight OCR packages...
echo Trying PaddleOCR (lightweight alternative)...
python -m pip install paddlepaddle --no-warn-script-location
python -m pip install paddleocr --no-warn-script-location
python -m pip install opencv-python --no-warn-script-location
if errorlevel 1 (
    echo PaddleOCR failed, trying EasyOCR...
    python -m pip install easyocr --no-warn-script-location
    if errorlevel 1 (
        echo WARNING: All OCR packages failed - using fallback text detection
        echo The app will still detect drops but without reading text
    ) else (
        echo ✓ EasyOCR installed as backup
    )
) else (
    echo ✓ PaddleOCR installed - lightweight text recognition ready!
)

echo Installing optional UI packages...
echo ✓ pystray already installed with core packages

echo Verifying core installation...
python -c "import keyboard, pynput, mss, numpy, PIL, requests, win32api, pystray; print('✓ All core packages installed')" 2>nul
if errorlevel 1 (
    echo ERROR: Core package installation failed
    echo.
    echo Trying with --user flag...
    python -m pip install --user keyboard pynput mss numpy pillow requests pywin32 pystray pytesseract opencv-python
    
    python -c "import keyboard, pynput, mss, numpy, PIL, requests, win32api, pystray; print('✓ Core packages installed with --user')" 2>nul
    if errorlevel 1 (
        echo ERROR: Installation failed completely
        echo.
        echo Possible solutions:
        echo 1. Run as administrator
        echo 2. Check your internet connection
        echo 3. Update Python to latest version
        echo 4. Disable antivirus temporarily
        echo.
        pause
        exit /b 1
    )
)
echo ✓ Packages installed successfully

echo.
echo [4/4] Final verification...
echo Checking essential modules...
python -c "import keyboard; print('✓ keyboard')" 2>nul || echo ✗ keyboard MISSING
python -c "import pynput; print('✓ pynput')" 2>nul || echo ✗ pynput MISSING
python -c "import mss; print('✓ mss')" 2>nul || echo ✗ mss MISSING
python -c "import numpy; print('✓ numpy')" 2>nul || echo ✗ numpy MISSING
python -c "import PIL; print('✓ pillow')" 2>nul || echo ✗ pillow MISSING
python -c "import requests; print('✓ requests')" 2>nul || echo ✗ requests MISSING
python -c "import win32api; print('✓ pywin32')" 2>nul || echo ✗ pywin32 MISSING
python -c "import pystray; print('✓ pystray')" 2>nul || echo ✗ pystray MISSING

echo Checking optional modules...
echo ✓ pystray already verified above
python -c "import paddleocr; print('✓ PaddleOCR (lightweight text recognition)')" 2>nul || python -c "import easyocr; print('✓ EasyOCR (text recognition)')" 2>nul || echo ✗ OCR (using fallback detection)
python -c "import cv2; print('✓ opencv-python (image processing)')" 2>nul || echo ✗ opencv-python (image processing disabled)

echo.
echo Testing basic functionality...
python -c "
import sys
try:
    import keyboard, pynput, mss, numpy, PIL, requests, win32api, pystray
    print('✓ All essential modules working')
    sys.exit(0)
except ImportError as e:
    print(f'✗ Missing module: {e}')
    sys.exit(1)
" 2>nul
if errorlevel 1 (
    echo.
    echo WARNING: Some essential modules are missing
    echo The program may not work correctly
    echo Try running the installer as administrator
)


echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo To run GPO Autofish:
echo   • Double-click "run.bat" (recommended)
echo   • Or run "python src/main.py" in command prompt
echo.
echo Features available:
echo   ✓ Auto-fishing with PD controller
echo   ✓ Auto-purchase system
echo   ✓ Discord webhook notifications
echo   ✓ System tray support
echo   ✓ Auto-recovery system
echo   ✓ Pause/Resume functionality
echo   ✓ Dual layout system (F2 to toggle)
echo   ✓ Text recognition for drops (OCR)
echo   ✓ Auto zoom control
echo.
echo OCR Status:
python -c "import paddleocr; print('✓ PaddleOCR ready - lightweight text recognition available')" 2>nul || python -c "import easyocr; print('✓ EasyOCR ready - text recognition available')" 2>nul || echo ⚠️  Using fallback detection - drops detected but text not readable
echo.
echo Press any key to exit...
pause >nul