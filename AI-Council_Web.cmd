@echo off
cd /d "%~dp0"
rem Runs in the background without a console window. Quit: the quit button in the app.
rem To see server messages, run AI-Council_Debug.cmd instead. Log: data\logs\server.log
where pythonw.exe >nul 2>nul
if errorlevel 1 goto console
start "" pythonw.exe "%~dp0ai_council_web.py"
exit /b 0

:console
python.exe "%~dp0ai_council_web.py"
if errorlevel 1 (
    echo.
    echo [AI Council] Server stopped with an error. Check the message above.
    pause
)
