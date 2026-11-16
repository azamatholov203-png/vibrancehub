@echo off
cd /d "%~dp0"
title VibranceHub builder

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ 64-bit from python.org
    pause
    exit /b 1
)

echo Installing PyInstaller...
python -m pip install --disable-pip-version-check pyinstaller
if errorlevel 1 (
    echo [ERROR] pip install failed. Check internet connection and try again.
    pause
    exit /b 1
)

echo.
echo Building VibranceHub.exe. This takes 2-5 minutes, please wait...
python -m PyInstaller --noconfirm --onefile --windowed --name VibranceHub --icon assets\icon.ico --add-data "assets;assets" main.py

echo.
if exist dist\VibranceHub.exe (
    echo [OK] Done. Your exe is: dist\VibranceHub.exe
    echo Note: the exe starts slowly on the first launch. That is normal.
) else (
    echo [ERROR] Build failed. Scroll up and read the last error lines.
)
echo.
pause
