@echo off
echo ============================================================
echo Building Standalone Windows Executable (FileInspector.exe)
echo ============================================================
call .\venv\Scripts\activate.bat
pip install pyinstaller
python build_exe.py
echo Build complete. Check dist\FileInspector.exe
pause
