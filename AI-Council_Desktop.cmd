@echo off
cd /d "%~dp0"
where pythonw.exe >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw.exe "%~dp0ai_council_desktop.py"
) else (
    python.exe "%~dp0ai_council_desktop.py"
)
