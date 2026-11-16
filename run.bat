@echo off
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ 64-bit from python.org
    echo and check "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

echo Installing dependencies, please wait...
python -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo [ERROR] pip install failed. Check internet connection and try again.
    pause
    exit /b 1
)

echo.
echo Starting VibranceHub...
start "" pythonw main.py
echo Started. If no window appeared, run run_debug.bat to see the error text.
