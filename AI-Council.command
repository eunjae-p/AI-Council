#!/bin/bash
# AI Council 실행 (macOS) — 서버를 백그라운드로 켜고 브라우저를 엽니다. 종료는 화면 왼쪽 아래 '앱 종료'.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
# 화면 언어: AI_COUNCIL_LANG(ko|en) → macOS 언어 설정 → LANG/LC_ALL. 그 외는 영어.
KO=0
case "${AI_COUNCIL_LANG:-}" in
  ko*) KO=1 ;;
  en*) KO=0 ;;
  *) case "$(defaults read -g AppleLanguages 2>/dev/null | sed -n 2p | tr -d ' ",')" in ko*) KO=1 ;; esac
     case "${LC_ALL:-}${LANG:-}" in ko*) KO=1 ;; esac ;;
esac
t() { if [ "$KO" = 1 ]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }
PY=""
for p in /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  command -v "$p" >/dev/null && "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null && { PY="$p"; break; }
done
if [ -z "$PY" ]; then echo "$(t 'Python 3.10 이상이 필요합니다. Setup-mac.command 를 먼저 실행하세요.' 'Python 3.10 or later is required. Run Setup-mac.command first.')"; read -r -p "$(t 'Enter 를 누르면 닫힙니다.' 'Press Enter to close.')"; exit 1; fi
mkdir -p data/logs
nohup "$PY" ai_council_web.py >> data/logs/server.log 2>&1 &
echo "$(t 'AI Council 을 시작했습니다. 잠시 후 브라우저가 열립니다.' 'AI Council has started. Your browser will open shortly.')"
echo "$(t "이 터미널 창은 닫아도 됩니다. (종료는 Council 화면 왼쪽 아래 '앱 종료')" "You can close this Terminal window. (To quit, use 'Quit app' at the bottom left of the Council screen.)")"
sleep 2
