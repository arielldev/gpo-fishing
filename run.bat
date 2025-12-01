@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Look for Python installations in order of preference
set PYTHON_EXE=

REM Skip Python 3.14+ - not supported

if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe" (
    set PYTHON_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe
    goto python_found
)

if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe" (
    set PYTHON_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe
    goto python_found
)

REM Try system python command
python --version >nul 2>&1
if not errorlevel 1 (
    REM Check if it's Python 3.14+ (not supported)
    python -c "import sys; exit(1 if sys.version_info >= (3, 14) else 0)" 2>nul
    if errorlevel 1 (
        echo ERROR: Python 3.14+ detected but not supported
        echo Please install Python 3.12 or 3.13 instead
        pause
        exit /b 1
    )
    set PYTHON_EXE=python
    goto python_found
)

REM Try py launcher as last resort
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_EXE=py -3
    goto python_found
)

REM If nothing found, show error and exit
echo ERROR: No compatible Python installation found
echo Please install Python 3.12 or 3.13 from https://python.org
echo Python 3.14+ is not supported due to package compatibility issues
pause
exit /b 1

:python_found
REM Check if virtual environment exists and activate it
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Use pythonw for no console window
if "!PYTHON_EXE!"=="python" (
    set PYTHONW_EXE=pythonw
) else if "!PYTHON_EXE!"=="py -3" (
    set PYTHONW_EXE=pyw -3
) else (
    set PYTHONW_EXE=!PYTHON_EXE:python.exe=pythonw.exe!
)
start "" "!PYTHONW_EXE!" src/main.py
exit