@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM Look for Python installations in order of preference
set PYTHON_EXE=

if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python314\python.exe" (
    set PYTHON_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python314\python.exe
    goto python_found
)

if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe" (
    set PYTHON_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313\python.exe
    goto python_found
)

if exist "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe" (
    set PYTHON_EXE=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe
    goto python_found
)

REM Fallback to py launcher
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_EXE=py -3
    goto python_found
)

REM If nothing found, exit
exit /b 1

:python_found
REM Check if virtual environment exists and activate it
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Use pythonw for no console window
set PYTHONW_EXE=!PYTHON_EXE:python.exe=pythonw.exe!
start "" "!PYTHONW_EXE!" src/main.py
exit