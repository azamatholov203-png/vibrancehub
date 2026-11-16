@echo off
cd /d "%~dp0"
title VibranceHub - debug console

echo Running VibranceHub with console output.
echo If it crashes, the error text will appear here.
echo.
python main.py
echo.
echo ---- App exited, exit code: %errorlevel% ----
pause
