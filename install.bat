@echo off
echo ========================================
echo   GPO Autofish - Easy Installation
echo ========================================
echo.

echo [1/4] Checking Python installation...

REM Set Python launcher environment to avoid py -3 issues
set PYLAUNCHER_NO_SEARCH_PATH=1
set PY_PYTHON=3

REM Try different Python commands
set PYTHON_CMD=
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto python_found
)

py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto python_found
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    goto python_found
)

echo ERROR: Python is not installed or not in PATH
echo.
echo Please install Python 3.8+ from https://python.org
echo Make sure to check "Add Python to PATH" during installation
echo.
pause
exit /b 1

:python_found

for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✓ Python %PYTHON_VERSION% found using: %PYTHON_CMD%

echo.
echo [2/4] Upgrading pip to latest version...
%PYTHON_CMD% -m pip install --upgrade pip >nul 2>&1
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
%PYTHON_CMD% -m pip install keyboard==0.13.5 --no-warn-script-location
%PYTHON_CMD% -m pip install pynput==1.8.1 --no-warn-script-location
%PYTHON_CMD% -m pip install mss==10.1.0 --no-warn-script-location
%PYTHON_CMD% -m pip install numpy --no-warn-script-location
%PYTHON_CMD% -m pip install pillow --no-warn-script-location
%PYTHON_CMD% -m pip install requests --no-warn-script-location
%PYTHON_CMD% -m pip install pywin32 --no-warn-script-location

echo Installing OCR packages for text recognition...
echo.
echo Installing OpenCV for image processing (required for OCR)...
%PYTHON_CMD% -m pip install opencv-python --no-warn-script-location
if errorlevel 1 (
    echo OpenCV installation failed, trying --user flag...
    %PYTHON_CMD% -m pip install --user opencv-python
    if errorlevel 1 (
        echo WARNING: OpenCV installation failed
        echo The app will use basic text detection without advanced OCR
    ) else (
        echo ✓ OpenCV installed with --user flag
    )
) else (
    echo ✓ OpenCV installed successfully
)



echo.
echo Installing optional advanced OCR (TrOCR - may be large download)...
%PYTHON_CMD% -m pip install transformers torch torchvision --index-url https://download.pytorch.org/whl/cpu --no-warn-script-location
if errorlevel 1 (
    echo Advanced OCR installation failed - using basic OCR only
    echo This is normal and the app will work fine with basic text detection
) else (
    echo ✓ Advanced TrOCR installed successfully
)

echo Verifying core installation...
%PYTHON_CMD% -c "import keyboard, pynput, mss, numpy, PIL, requests, win32api; print('✓ All core packages installed')" 2>nul
if errorlevel 1 (
    echo ERROR: Core package installation failed
    echo.
    echo Trying with --user flag...
    %PYTHON_CMD% -m pip install --user keyboard pynput mss numpy pillow requests pywin32 opencv-python
    
    %PYTHON_CMD% -c "import keyboard, pynput, mss, numpy, PIL, requests, win32api; print('✓ Core packages installed with --user')" 2>nul
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
%PYTHON_CMD% -c "import keyboard; print('✓ keyboard')" 2>nul || echo ✗ keyboard MISSING
%PYTHON_CMD% -c "import pynput; print('✓ pynput')" 2>nul || echo ✗ pynput MISSING
%PYTHON_CMD% -c "import mss; print('✓ mss')" 2>nul || echo ✗ mss MISSING
%PYTHON_CMD% -c "import numpy; print('✓ numpy')" 2>nul || echo ✗ numpy MISSING
%PYTHON_CMD% -c "import PIL; print('✓ pillow')" 2>nul || echo ✗ pillow MISSING
%PYTHON_CMD% -c "import requests; print('✓ requests')" 2>nul || echo ✗ requests MISSING
%PYTHON_CMD% -c "import win32api; print('✓ pywin32')" 2>nul || echo ✗ pywin32 MISSING

echo Checking OCR modules...
%PYTHON_CMD% -c "import cv2; print('✓ opencv-python (image processing available)')" 2>nul || echo ✗ opencv-python (image processing disabled)
%PYTHON_CMD% -c "import transformers; print('✓ TrOCR (advanced text recognition available)')" 2>nul || echo ✗ TrOCR (advanced OCR disabled - using basic OCR only)

echo.
echo Testing basic functionality...
%PYTHON_CMD% -c "import keyboard, pynput, mss, numpy, PIL, requests, win32api; print('✓ All essential modules working')" 2>nul
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
%PYTHON_CMD% -c "import cv2, numpy, PIL; print('✓ Basic OCR ready - text detection available!')" 2>nul && %PYTHON_CMD% -c "import transformers; print('✓ Advanced TrOCR ready - enhanced text recognition available!')" 2>nul || echo ⚠️  Basic OCR only (advanced TrOCR not available)
echo.
echo Press any key to exit...
pause >nul