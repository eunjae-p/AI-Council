@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
rem 업데이트 중 이 파일이 바뀌어도 안전하도록 전체를 한 블록으로 읽어 실행
(
  python.exe "%~dp0council_update.py"
  echo.
  pause
  exit /b
)
