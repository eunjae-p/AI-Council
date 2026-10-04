"""설치된 CLI 버전과 최신 버전 확인 (구독 사용량을 쓰지 않음).

- 설치 버전: `codex --version`, `claude --version`
- 최신 버전: npm 레지스트리 조회 (인터넷이 안 되면 건너뜀)
업데이트는 하지 않는다. 화면에 안내만 한다.
"""
from __future__ import annotations

import json
import re
import subprocess
import threading
import time
import urllib.request

from council_core import CliFailure, resolve_command

PACKAGES = {"codex": "@openai/codex", "claude": "@anthropic-ai/claude-code"}
UPDATE_COMMANDS = {"codex": "npm i -g @openai/codex@latest", "claude": "claude update"}
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
        result[name] = {
            "installed": inst,
            "latest": late,
            "outdated": bool(inst and late and newer(late, inst)),
            "update_command": UPDATE_COMMANDS[name],
        }
    result["checked_at"] = time.time()
    return result
