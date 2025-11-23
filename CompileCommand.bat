@echo off
REM Compile GPO Fishing Macro to EXE using PyInstaller
REM Make sure PyInstaller is installed: pip install pyinstaller

echo ========================================
echo  GPO Fishing Macro - Build Script
echo ========================================
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ERROR: PyInstaller not found!
    echo Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Check if Pillow is installed for icon conversion
python -c "import PIL" 2>nul
if errorlevel 1 (
    echo Installing Pillow for icon conversion...
    pip install Pillow
)

REM Convert webp icon to ico format
echo Converting icon...
python -c "from PIL import Image; img = Image.open('images/icon.webp'); img.save('icon.ico')"

echo Building EXE...
echo.

REM Build the executable with icon and version info
pyinstaller --onefile --windowed --name "GPO_Fishing_Macro" --icon=icon.ico --version-file=version_info.txt src/main.py

if errorlevel 1 (
    echo.
    echo BUILD FAILED!
    pause
    exit /b 1
)

REM Clean up temporary files
if exist icon.ico del icon.ico

echo.
echo ========================================
echo  Build Complete!
echo  Output: dist\GPO_Fishing_Macro.exe
echo ========================================
echo.
echo NOTE: To fully remove the "Unknown Publisher" warning,
echo you would need to digitally sign the executable with
echo a code signing certificate from a trusted CA.
echo.
pause
