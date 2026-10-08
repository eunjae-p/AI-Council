"""설치된 CLI 버전과 최신 버전 확인 (구독 사용량을 쓰지 않음).

- 설치 버전: `codex --version`, `claude --version`
- 최신 버전: npm 레지스트리 조회 (인터넷이 안 되면 건너뜀)
업데이트는 하지 않는다. 화면에 안내만 한다.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
import urllib.request

from council_core import CliFailure, resolve_command

PACKAGES = {"codex": "@openai/codex", "claude": "@anthropic-ai/claude-code"}
# Windows PowerShell 은 npm 이 만든 codex.ps1 / npm.ps1 을 실행 정책 때문에 막는 경우가 많다.
# .cmd 로 부르면 PowerShell·명령 프롬프트 어디서든 실행 정책과 상관없이 동작한다.
_W = ".cmd" if os.name == "nt" else ""
UPDATE_COMMANDS = {"codex": f"npm{_W} i -g @openai/codex@latest", "claude": "claude update"}
_VER = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_cache: dict[str, tuple[float, object]] = {}
_lock = threading.Lock()


def _cached(key: str, ttl: float, fn):
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
    value = fn()
    with _lock:
        _cache[key] = (time.time(), value)
    return value


def parse(text: str) -> str:
    m = _VER.search(text or "")
    return ".".join(m.groups()) if m else ""


def newer(latest: str, installed: str) -> bool:
    try:
        return tuple(map(int, latest.split("."))) > tuple(map(int, installed.split(".")))
    except ValueError:
        return False


def installed_version(name: str) -> str:
    try:
        out = subprocess.run(
            resolve_command(name) + ["--version"], capture_output=True, timeout=20, stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return parse(out.stdout.decode("utf-8", "replace") + out.stderr.decode("utf-8", "replace"))
    except (CliFailure, OSError, subprocess.TimeoutExpired):
        return ""


LOGIN_ARGS = {"codex": ["login", "status"], "claude": ["auth", "status"]}
LOGIN_COMMANDS = {"codex": f"codex{_W} login", "claude": "claude auth login"}


def logged_in(name: str) -> bool | None:
    """로그인 여부. 확인할 수 없으면 None (구독 사용량을 쓰지 않는 상태 확인 명령)."""
    try:
        out = subprocess.run(
            resolve_command(name) + LOGIN_ARGS[name], capture_output=True, timeout=20, stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (CliFailure, OSError, subprocess.TimeoutExpired):
        return None
    text = (out.stdout + out.stderr).decode("utf-8", "replace").lower()
    if any(k in text for k in ("unknown", "unrecognized", "unexpected argument")):
        return None  # 구버전 CLI 가 상태 확인 명령을 모름
    return out.returncode == 0


def latest_version(name: str) -> str:
    try:
        url = f"https://registry.npmjs.org/{PACKAGES[name]}/latest"
        with urllib.request.urlopen(url, timeout=6) as res:
            return parse(str(json.loads(res.read().decode("utf-8")).get("version", "")))
    except Exception:
        return ""


def check(force: bool = False) -> dict:
    if force:
        with _lock:
            _cache.clear()
    result = {}
    for name in ("codex", "claude"):
        inst = _cached(f"inst:{name}", 600, lambda n=name: installed_version(n))
        late = _cached(f"late:{name}", 6 * 3600, lambda n=name: latest_version(n))
        login = _cached(f"login:{name}", 600, lambda n=name: logged_in(n)) if inst else None
        result[name] = {
            "installed": inst,
            "logged_in": login,
            "login_command": LOGIN_COMMANDS[name],
            "latest": late,
            "outdated": bool(inst and late and newer(late, inst)),
            "update_command": UPDATE_COMMANDS[name],
        }
    result["checked_at"] = time.time()
    return result
