#!/bin/bash
# AI Council 업데이트 (macOS) — 웹 화면 없이 GitHub 최신 버전을 받습니다.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"
PY=python3; for p in /opt/homebrew/bin/python3 /usr/local/bin/python3; do [ -x "$p" ] && { PY="$p"; break; }; done
"$PY" council_update.py
echo; read -r -p "Enter 를 누르면 닫힙니다."
