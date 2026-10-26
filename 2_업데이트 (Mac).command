#!/bin/bash
# GitHub 최신 버전 받기 / Update from GitHub
# (같은 폴더의 Update-mac.command 를 실행합니다 / runs Update-mac.command in this folder)
exec "$(cd "$(dirname "$0")" && pwd)/Update-mac.command" "$@"
