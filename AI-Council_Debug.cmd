@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
rem 문제 확인용: 콘솔 창에 서버 메시지를 보여 주며 실행합니다. (Ctrl+C 로 종료)
python.exe "%~dp0ai_council_web.py"
echo.
pause
