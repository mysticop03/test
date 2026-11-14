@echo off
title Building FileInspector.exe
cd /d "%~dp0"

echo ========================================================
echo       Building Standalone Windows FileInspector.exe    
echo ========================================================
echo.

if exist "venv\Scripts\python.exe" (
    call venv\Scripts\python.exe build_exe.py
) else (
    python build_exe.py
)

pause
