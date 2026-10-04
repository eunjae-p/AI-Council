@echo off
cd /d "%~dp0"
python.exe "%~dp0ai_council_web.py"
if errorlevel 1 (
    echo.
    echo [AI Council] Server stopped with an error. Check the message above.
    pause
)
