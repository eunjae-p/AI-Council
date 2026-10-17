#!/bin/bash
# AI Council 설치 도우미 (macOS) — Finder 에서 더블클릭하면 터미널에서 실행됩니다.
# 하는 일: Xcode 명령줄 도구(git) · Homebrew · Python · Node.js · ffmpeg · Codex CLI · Claude Code 확인/설치
#          → 로그인 안내 → 바탕화면에 "AI Council" 실행 아이콘 만들기
cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
RESULTS=()
# 화면 언어: AI_COUNCIL_LANG(ko|en) → macOS 언어 설정 → LANG/LC_ALL. 그 외는 영어.
KO=0
case "${AI_COUNCIL_LANG:-}" in
  ko*) KO=1 ;;
  en*) KO=0 ;;
  *) case "$(defaults read -g AppleLanguages 2>/dev/null | sed -n 2p | tr -d ' ",')" in ko*) KO=1 ;; esac
     case "${LC_ALL:-}${LANG:-}" in ko*) KO=1 ;; esac ;;
esac
t() { if [ "$KO" = 1 ]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }
step() { echo; echo "▶ $1"; }
ok()   { echo "  ✓ $1"; }
warn() { echo "  ! $1"; }
bad()  { echo "  ✗ $1"; }
add()  { RESULTS+=("$1|$2|$3"); }
ask()  { read -r -p "  $1 (Y/n) " a; [[ -z "$a" || "$a" =~ ^([Yy]|ㅛ|예) ]]; }
load_brew() {
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [ -x "$b" ] && eval "$("$b" shellenv)" && return 0; done
  return 1
}
export PATH="$HOME/.local/bin:$PATH"
load_brew

FAIL="$(t '실패' 'Failed')"
NEW="$(t '새로 설치' 'newly installed')"

echo "============================================"
echo "  $(t 'AI Council 설치 도우미 (Mac)' 'AI Council Setup (Mac)')"
echo "============================================"

# 1) Xcode 명령줄 도구 (git 포함) ------------------------------------------
step "$(t '1/7 Xcode 명령줄 도구 확인 (git 포함)' '1/7 Checking Xcode Command Line Tools (includes git)')"
if xcode-select -p >/dev/null 2>&1 && command -v git >/dev/null; then
  ok "$(t '설치됨' 'Installed') ($(git --version))"; add "Git" "OK" "$(git --version | awk '{print $3}')"
else
  warn "$(t '설치 창이 열립니다. 설치를 마친 뒤 이 파일을 다시 실행하세요.' 'An installer window will open. Run this file again after the installation finishes.')"
  xcode-select --install >/dev/null 2>&1
  add "Git" "$(t '설치 중' 'Installing')" "$(t '설치 후 Setup-mac.command 다시 실행' 'Run Setup-mac.command again after installing')"
fi

# 2) Homebrew ----------------------------------------------------------
step "$(t '2/7 Homebrew 확인 (Mac 프로그램 설치 도구)' '2/7 Checking Homebrew (Mac package manager)')"
if command -v brew >/dev/null; then
  ok "$(t '설치됨' 'Installed')"; add "Homebrew" "OK" ""
else
  warn "$(t 'Homebrew가 없습니다. 공식 설치 프로그램을 실행합니다 (Mac 로그인 비밀번호를 물을 수 있습니다).' 'Homebrew not found. Running the official installer (it may ask for your Mac login password).')"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if load_brew; then ok "$(t '설치 완료' 'Installed')"; add "Homebrew" "OK" "$NEW"
  else bad "$(t '설치 실패' 'Installation failed')"; add "Homebrew" "$FAIL" "$(t 'https://brew.sh 참고' 'See https://brew.sh')"; fi
fi

# 3) Python 3.10 이상 ----------------------------------------------------
step "$(t '3/7 Python 확인 (3.10 이상 필요)' '3/7 Checking Python (3.10 or later required)')"
pick_python() {
  for p in /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
    command -v "$p" >/dev/null || continue
    "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null && { echo "$p"; return 0; }
  done; return 1
}
PY="$(pick_python)"
if [ -z "$PY" ] && command -v brew >/dev/null; then warn "$(t 'Python 3.10 이상을 설치합니다.' 'Installing Python 3.10 or later.')"; brew install python; PY="$(pick_python)"; fi
if [ -n "$PY" ]; then ok "$($PY --version)"; add "Python" "OK" "$($PY --version | awk '{print $2}')"
else bad "$(t 'Python 3.10 이상이 없습니다' 'Python 3.10 or later not found')"; add "Python" "$FAIL" "brew install python"; fi

# 4) Node.js · ffmpeg ----------------------------------------------------
step "$(t '4/7 Node.js (Codex CLI 설치용) · ffmpeg (영상 분석용) 확인' '4/7 Checking Node.js (for Codex CLI) and ffmpeg (for video analysis)')"
for pkg in node ffmpeg; do
  if command -v "$pkg" >/dev/null; then ok "$pkg $(t '설치됨' 'installed')"; add "$pkg" "OK" ""
  elif command -v brew >/dev/null; then
    brew install "$pkg" && { ok "$pkg $(t '설치 완료' 'installed')"; add "$pkg" "OK" "$NEW"; } || { bad "$pkg $(t '설치 실패' 'installation failed')"; add "$pkg" "$FAIL" "brew install $pkg"; }
  else bad "$pkg $(t '없음 (Homebrew 필요)' 'not found (Homebrew required)')"; add "$pkg" "$FAIL" "$(t 'Homebrew 설치 후 다시 실행' 'Install Homebrew, then run again')"; fi
done

# 5) Codex CLI ---------------------------------------------------------
step "$(t '5/7 Codex CLI 설치/업데이트 (GPT 연결용)' '5/7 Installing/updating Codex CLI (for GPT)')"
if command -v npm >/dev/null; then npm install -g @openai/codex@latest >/dev/null 2>&1; fi
if command -v codex >/dev/null; then v="$(codex --version 2>/dev/null)"; ok "Codex CLI $v"; add "Codex CLI" "OK" "$v"
else bad "$(t 'Codex CLI 설치 실패' 'Codex CLI installation failed')"; add "Codex CLI" "$FAIL" "npm install -g @openai/codex@latest"; fi

# 6) Claude Code -------------------------------------------------------
step "$(t '6/7 Claude Code 확인 (Claude 연결용)' '6/7 Checking Claude Code (for Claude)')"
if ! command -v claude >/dev/null; then
  warn "$(t 'Claude Code를 공식 설치 프로그램으로 설치합니다.' 'Installing Claude Code with the official installer.')"
  curl -fsSL https://claude.ai/install.sh | bash
  export PATH="$HOME/.local/bin:$PATH"
fi
if command -v claude >/dev/null; then v="$(claude --version 2>/dev/null)"; ok "Claude Code $v"; add "Claude Code" "OK" "$v"
else bad "$(t 'Claude Code 설치 실패' 'Claude Code installation failed')"; add "Claude Code" "$FAIL" "https://claude.ai/install.sh"; fi

# 7) 로그인 -------------------------------------------------------------
step "$(t '7/7 로그인 확인 (각자 자기 구독 계정, 브라우저에서 진행)' '7/7 Checking sign-in (each person uses their own subscription, in the browser)')"
NEED="$(t '필요' 'Needed')"
if command -v codex >/dev/null; then
  if codex login status >/dev/null 2>&1; then ok "$(t 'GPT(Codex): 로그인됨' 'GPT (Codex): signed in')"; add "$(t 'Codex 로그인' 'Codex login')" "OK" ""
  else warn "$(t 'GPT(Codex): 로그인 필요 — ChatGPT 계정' 'GPT (Codex): sign-in required — ChatGPT account')"
    ask "$(t '지금 로그인할까요?' 'Sign in now?')" && codex login
    codex login status >/dev/null 2>&1 && { ok "$(t '로그인됨' 'Signed in')"; add "$(t 'Codex 로그인' 'Codex login')" "OK" ""; } || add "$(t 'Codex 로그인' 'Codex login')" "$NEED" "$(t '터미널에서 codex login' 'Run codex login in Terminal')"
  fi
fi
if command -v claude >/dev/null; then
  if claude auth status >/dev/null 2>&1; then ok "$(t 'Claude: 로그인됨' 'Claude: signed in')"; add "$(t 'Claude 로그인' 'Claude login')" "OK" ""
  else warn "$(t 'Claude: 로그인 필요 — Claude Pro/Max 계정' 'Claude: sign-in required — Claude Pro/Max account')"
    ask "$(t '지금 로그인할까요?' 'Sign in now?')" && claude auth login
    claude auth status >/dev/null 2>&1 && { ok "$(t '로그인됨' 'Signed in')"; add "$(t 'Claude 로그인' 'Claude login')" "OK" ""; } || add "$(t 'Claude 로그인' 'Claude login')" "$NEED" "$(t '터미널에서 claude auth login' 'Run claude auth login in Terminal')"
  fi
fi

# 바탕화면 실행 아이콘 ---------------------------------------------------
chmod +x "$ROOT"/*.command 2>/dev/null
LAUNCH="$HOME/Desktop/AI Council.command"
cat > "$LAUNCH" <<LAUNCHER
#!/bin/bash
exec "$ROOT/AI-Council.command"
LAUNCHER
chmod +x "$LAUNCH" && ok "$(t "바탕화면에 'AI Council' 실행 아이콘을 만들었습니다." "Created an 'AI Council' launcher on your Desktop.")"

echo
echo "============ $(t '설치 결과' 'Setup results') ============"
for r in "${RESULTS[@]}"; do IFS='|' read -r n s m <<<"$r"; printf "  %-14s %-8s %s\n" "$n" "$s" "$m"; done
echo
echo "$(t "바탕화면의 'AI Council'을 더블클릭하면 실행됩니다." "Double-click 'AI Council' on your Desktop to start it.")"
echo "$(t '이 창은 닫아도 됩니다.' 'You can close this window.')"
