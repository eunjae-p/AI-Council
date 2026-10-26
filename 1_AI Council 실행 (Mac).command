#!/bin/bash
# AI Council 실행 / Start AI Council
# (같은 폴더의 AI-Council.command 를 실행합니다 / runs AI-Council.command in this folder)
exec "$(cd "$(dirname "$0")" && pwd)/AI-Council.command" "$@"
