#!/bin/bash
# AI Council 업데이트 (macOS) — 웹 화면 없이 GitHub 최신 버전을 받습니다.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
# 화면 언어: AI_COUNCIL_LANG(ko|en) → macOS 언어 설정 → LANG/LC_ALL. 그 외는 영어. (council_update.py 에도 전달)
KO=0
case "${AI_COUNCIL_LANG:-}" in
  ko*) KO=1 ;;
  en*) KO=0 ;;
  *) case "$(defaults read -g AppleLanguages 2>/dev/null | sed -n 2p | tr -d ' ",')" in ko*) KO=1 ;; esac
     case "${LC_ALL:-}${LANG:-}" in ko*) KO=1 ;; esac ;;
esac
t() { if [ "$KO" = 1 ]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }
[ -z "${AI_COUNCIL_LANG:-}" ] && export AI_COUNCIL_LANG="$(t ko en)"
PY=python3; for p in /opt/homebrew/bin/python3 /usr/local/bin/python3; do [ -x "$p" ] && { PY="$p"; break; }; done
"$PY" council_update.py
echo; read -r -p "$(t 'Enter 를 누르면 닫힙니다.' 'Press Enter to close.')"
