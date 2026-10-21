"""작업 모드의 명령 실행 허용 목록 — 승인 기반 (MCP 와 같은 방식).

원칙
- 작업 모드에서 Claude 는 파일 읽기·만들기·고치기와 명령 실행(Bash)을 할 수 있다.
- 명령은 **허용 목록에 있는 명령으로 시작할 때만** 묻지 않고 실행된다 (Claude Code --allowedTools "Bash(mkdir:*)").
- 목록에 없는 명령은 CLI 가 실행을 거부하고(permission_denials), Council 이 화면에 명령과 함께
  "이번만 허용 / 항상 허용 / 허용 안 함"을 보여 준다. 허용하면 같은 질문을 다시 실행한다.
- 허용 단위는 명령 앞부분(접두어)이다. 예: `npm install express` → `npm install`.
  접두어는 영문·숫자·공백·. _ - / 만 허용한다 (따옴표·&·| 등이 들어간 규칙은 만들지 않음).
- 모든 명령을 묻지 않고 실행하는 모드(bypassPermissions)는 쓰지 않는다.

저장 (Git 제외): data/cmd_settings.json — 사용자가 고친 허용 목록
"""
from __future__ import annotations

import json
import os
import re
import shlex
import threading
from pathlib import Path

# 처음 허용 목록: 확인·폴더 만들기·버전 확인처럼 되돌리기 쉬운 명령만
DEFAULT_PREFIXES = [
    "ls", "pwd", "dir", "cat", "head", "tail", "wc", "echo", "which", "where", "tree",
    "mkdir", "touch",
    "git status", "git diff", "git log", "git init", "git add",
    "python --version", "python3 --version", "node --version", "npm --version",
]
# 🛡 "개발 명령 한 번에 허용" 버튼: 코드 작성·실행·설치에 자주 쓰는 명령 (사용자가 누를 때만 추가)
DEV_PRESET = ["node", "npm", "npx", "python", "python3", "py", "pip", "pip3", "uv", "git"]
# 두 단어까지 접두어로 쓰는 명령 (npm install, git commit, pip install …)
TWO_WORD = {"git", "npm", "npx", "pnpm", "yarn", "pip", "pip3", "uv", "cargo", "docker", "brew", "winget", "conda", "go"}
# 인터프리터는 사실상 무엇이든 실행할 수 있다 → 화면에서 따로 경고
POWERFUL = {"python", "python3", "py", "node", "bash", "sh", "zsh", "powershell", "pwsh", "cmd", "rm", "del",
            "rmdir", "curl", "wget", "sudo", "npx", "mv", "chmod", "chown"}
_PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._/\-]{0,59}$")
_SPLIT_RE = re.compile(r"&&|\|\||;|\||\n")
_lock = threading.Lock()


def valid_prefix(prefix: object) -> bool:
    return isinstance(prefix, str) and bool(_PREFIX_RE.match(prefix.strip())) and "  " not in prefix


def prefixes_for(command: str) -> list[str]:
    """명령 문자열 → 허용할 접두어 목록 (&&, |, ; 로 이어진 명령은 각각)."""
    out: list[str] = []
    for part in _SPLIT_RE.split(str(command or "")):
        part = part.strip()
        if not part:
            continue
        try:
            words = shlex.split(part, posix=True)
        except ValueError:
            words = part.split()
        while words and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):  # FOO=1 cmd → cmd
            words = words[1:]
        if not words:
            continue
        first = os.path.basename(words[0]).lower()
        if first.endswith(".exe"):
            first = first[:-4]
        prefix = first
        if first in TWO_WORD and len(words) > 1 and re.match(r"^[A-Za-z][A-Za-z0-9_-]*$", words[1]):
            prefix = f"{first} {words[1]}"
        if first == "cd":
            continue  # 폴더 이동은 항상 허용 (작업 폴더 밖 쓰기는 CLI 가 따로 막음)
        if valid_prefix(prefix) and prefix not in out:
            out.append(prefix)
    return out


def is_powerful(prefix: str) -> bool:
    return prefix.split(" ")[0] in POWERFUL


def rules(prefixes: list[str]) -> list[str]:
    """접두어 → Claude Code 허용 규칙. cd 는 늘 허용."""
    return ["Bash(cd:*)"] + [f"Bash({p}:*)" for p in prefixes if valid_prefix(p)]


class CommandStore:
    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / "cmd_settings.json"

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def allowed(self) -> list[str]:
        data = self._load()
        items = data.get("allowed") if isinstance(data.get("allowed"), list) else DEFAULT_PREFIXES
        return [p for p in items if valid_prefix(p)]

    def set_allowed(self, prefix: str, allow: bool) -> list[str]:
        prefix = str(prefix or "").strip()
        if not valid_prefix(prefix):
            raise ValueError("명령 접두어가 올바르지 않습니다.")
        with _lock:
            current = self.allowed()
            if allow and prefix not in current:
                current.append(prefix)
            if not allow:
                current = [p for p in current if p != prefix]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps({"allowed": current}, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
            return current

    def reset(self) -> list[str]:
        with _lock:
            try:
                self.path.unlink()
            except OSError:
                pass
        return self.allowed()

    def state(self) -> dict:
        return {"allowed": [{"prefix": p, "powerful": is_powerful(p)} for p in self.allowed()],
                "defaults": DEFAULT_PREFIXES}
