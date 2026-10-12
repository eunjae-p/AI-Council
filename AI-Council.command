#!/bin/bash
# AI Council 실행 (macOS) — 서버를 백그라운드로 켜고 브라우저를 엽니다. 종료는 화면 왼쪽 아래 '앱 종료'.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
PY=""
for p in /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  command -v "$p" >/dev/null && "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null && { PY="$p"; break; }
done
if [ -z "$PY" ]; then echo "Python 3.10 이상이 필요합니다. Setup-mac.command 를 먼저 실행하세요."; read -r -p "Enter 를 누르면 닫힙니다."; exit 1; fi
mkdir -p data/logs
nohup "$PY" ai_council_web.py >> data/logs/server.log 2>&1 &
echo "AI Council 을 시작했습니다. 잠시 후 브라우저가 열립니다."
echo "이 터미널 창은 닫아도 됩니다. (종료는 Council 화면 왼쪽 아래 '앱 종료')"
sleep 2
