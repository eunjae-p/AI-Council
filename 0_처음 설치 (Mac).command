#!/bin/bash
# 처음 한 번: 설치·로그인·바탕화면 실행 아이콘 / First run: install, sign in, desktop launcher
# (같은 폴더의 Setup-mac.command 를 실행합니다 / runs Setup-mac.command in this folder)
exec "$(cd "$(dirname "$0")" && pwd)/Setup-mac.command" "$@"
