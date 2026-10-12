#!/bin/bash
# AI Council 설치 도우미 (macOS) — Finder 에서 더블클릭하면 터미널에서 실행됩니다.
# 하는 일: Xcode 명령줄 도구(git) · Homebrew · Python · Node.js · ffmpeg · Codex CLI · Claude Code 확인/설치
#          → 로그인 안내 → 바탕화면에 "AI Council" 실행 아이콘 만들기
cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
RESULTS=()
step() { echo; echo "▶ $1"; }
ok()   { echo "  ✓ $1"; }
warn() { echo "  ! $1"; }
bad()  { echo "  ✗ $1"; }
add()  { RESULTS+=("$1|$2|$3"); }
ask()  { read -r -p "  $1 (Y/n) " a; [[ -z "$a" || "$a" =~ ^[YyㅛYy] ]]; }
load_brew() {
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$b" ] && eval "$("$b" shellenv)" && return 0; done
  return 1
}
export PATH="$HOME/.local/bin:$PATH"
load_brew

echo "============================================"
echo "  AI Council 설치 도우미 (Mac)"
echo "============================================"

# 1) Xcode 명령줄 도구 (git 포함) ------------------------------------------
step "1/7 Xcode 명령줄 도구 확인 (git 포함)"
if xcode-select -p >/dev/null 2>&1 && command -v git >/dev/null; then
  ok "설치됨 ($(git --version))"; add "Git" "OK" "$(git --version | awk '{print $3}')"
else
  warn "설치 창이 열립니다. 설치를 마친 뒤 이 파일을 다시 실행하세요."
  xcode-select --install >/dev/null 2>&1
  add "Git" "설치 중" "설치 후 Setup-mac.command 다시 실행"
fi

# 2) Homebrew ----------------------------------------------------------
step "2/7 Homebrew 확인 (Mac 프로그램 설치 도구)"
if command -v brew >/dev/null; then
  ok "설치됨"; add "Homebrew" "OK" ""
else
  warn "Homebrew가 없습니다. 공식 설치 프로그램을 실행합니다 (Mac 로그인 비밀번호를 물을 수 있습니다)."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if load_brew; then ok "설치 완료"; add "Homebrew" "OK" "새로 설치"
  else bad "설치 실패"; add "Homebrew" "실패" "https://brew.sh 참고"; fi
fi

# 3) Python 3.10 이상 ----------------------------------------------------
step "3/7 Python 확인 (3.10 이상 필요)"
pick_python() {
  for p in /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
    command -v "$p" >/dev/null || continue
    "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null && { echo "$p"; return 0; }
  done; return 1
}
PY="$(pick_python)"
if [ -z "$PY" ] && command -v brew >/dev/null; then warn "Python 3.10 이상을 설치합니다."; brew install python; PY="$(pick_python)"; fi
if [ -n "$PY" ]; then ok "$($PY --version)"; add "Python" "OK" "$($PY --version | awk '{print $2}')"
else bad "Python 3.10 이상이 없습니다"; add "Python" "실패" "brew install python"; fi

# 4) Node.js · ffmpeg ----------------------------------------------------
step "4/7 Node.js (Codex CLI 설치용) · ffmpeg (영상 분석용) 확인"
for pkg in node ffmpeg; do
  if command -v "$pkg" >/dev/null; then ok "$pkg 설치됨"; add "$pkg" "OK" ""
  elif command -v brew >/dev/null; then
    brew install "$pkg" && { ok "$pkg 설치 완료"; add "$pkg" "OK" "새로 설치"; } || { bad "$pkg 설치 실패"; add "$pkg" "실패" "brew install $pkg"; }
  else bad "$pkg 없음 (Homebrew 필요)"; add "$pkg" "실패" "Homebrew 설치 후 다시 실행"; fi
done

# 5) Codex CLI ---------------------------------------------------------
step "5/7 Codex CLI 설치/업데이트 (GPT 연결용)"
if command -v npm >/dev/null; then npm install -g @openai/codex@latest >/dev/null 2>&1; fi
if command -v codex >/dev/null; then v="$(codex --version 2>/dev/null)"; ok "Codex CLI $v"; add "Codex CLI" "OK" "$v"
else bad "Codex CLI 설치 실패"; add "Codex CLI" "실패" "npm install -g @openai/codex@latest"; fi

# 6) Claude Code -------------------------------------------------------
step "6/7 Claude Code 확인 (Claude 연결용)"
if ! command -v claude >/dev/null; then
  warn "Claude Code를 공식 설치 프로그램으로 설치합니다."
  curl -fsSL https://claude.ai/install.sh | bash
  export PATH="$HOME/.local/bin:$PATH"
fi
if command -v claude >/dev/null; then v="$(claude --version 2>/dev/null)"; ok "Claude Code $v"; add "Claude Code" "OK" "$v"
else bad "Claude Code 설치 실패"; add "Claude Code" "실패" "https://claude.ai/install.sh"; fi

# 7) 로그인 -------------------------------------------------------------
step "7/7 로그인 확인 (각자 자기 구독 계정, 브라우저에서 진행)"
if command -v codex >/dev/null; then
  if codex login status >/dev/null 2>&1; then ok "GPT(Codex): 로그인됨"; add "Codex 로그인" "OK" ""
  else warn "GPT(Codex): 로그인 필요 — ChatGPT 계정"
    ask "지금 로그인할까요?" && codex login
    codex login status >/dev/null 2>&1 && { ok "로그인됨"; add "Codex 로그인" "OK" ""; } || add "Codex 로그인" "필요" "터미널에서 codex login"
  fi
fi
if command -v claude >/dev/null; then
  if claude auth status >/dev/null 2>&1; then ok "Claude: 로그인됨"; add "Claude 로그인" "OK" ""
  else warn "Claude: 로그인 필요 — Claude Pro/Max 계정"
    ask "지금 로그인할까요?" && claude auth login
    claude auth status >/dev/null 2>&1 && { ok "로그인됨"; add "Claude 로그인" "OK" ""; } || add "Claude 로그인" "필요" "터미널에서 claude auth login"
  fi
fi

# 바탕화면 실행 아이콘 ---------------------------------------------------
chmod +x "$ROOT"/*.command 2>/dev/null
LAUNCH="$HOME/Desktop/AI Council.command"
cat > "$LAUNCH" <<LAUNCHER
#!/bin/bash
exec "$ROOT/AI-Council.command"
LAUNCHER
chmod +x "$LAUNCH" && ok "바탕화면에 'AI Council' 실행 아이콘을 만들었습니다."

echo
echo "============ 설치 결과 ============"
for r in "${RESULTS[@]}"; do IFS='|' read -r n s m <<<"$r"; printf "  %-14s %-8s %s\n" "$n" "$s" "$m"; done
echo
echo "바탕화면의 'AI Council'을 더블클릭하면 실행됩니다."
echo "이 창은 닫아도 됩니다."
