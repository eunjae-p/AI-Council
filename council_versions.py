"""설치된 CLI 버전과 최신 버전 확인 (구독 사용량을 쓰지 않음).

- 설치 버전: `codex --version`, `claude --version`
- 최신 버전: npm 레지스트리 조회 (인터넷이 안 되면 건너뜀)
- 업데이트: 화면의 버튼으로 이 PC에서 바로 실행 (update_cli). 터미널 명령을 몰라도 된다.
- 로그인: 로그인 창(터미널)을 대신 열어 준다 (open_login). 브라우저 로그인은 사용자가 직접.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request

from council_core import CliFailure, decode_output, resolve_command, win_cmdline

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
            win_cmdline(resolve_command(name) + ["--version"]), capture_output=True, timeout=20, stdin=subprocess.DEVNULL,
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
            win_cmdline(resolve_command(name) + LOGIN_ARGS[name]), capture_output=True, timeout=20, stdin=subprocess.DEVNULL,
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


# ---------- 화면 버튼으로 업데이트 ----------
UPDATE_TIMEOUT = 600
NAMES = {"codex": "GPT (Codex CLI)", "claude": "Claude (Claude Code)"}


def _npm_command() -> list[str]:
    exe = shutil.which("npm")
    if not exe and os.name == "nt":  # Node.js 를 방금 설치해 PATH 가 아직 반영되지 않은 경우
        for base in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("APPDATA", "")):
            for cand in (os.path.join(base, "nodejs", "npm.cmd"), os.path.join(base, "npm", "npm.cmd")):
                if base and os.path.isfile(cand):
                    exe = cand
                    break
            if exe:
                break
    if not exe:
        raise CliFailure("npm", "Node.js(npm)를 찾을 수 없습니다. Council 폴더의 Setup.cmd를 실행해 설치하세요.")
    if exe.lower().endswith((".cmd", ".bat")):
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", exe]
    return [exe]


def update_args(name: str) -> list[str]:
    if name == "codex":
        return _npm_command() + ["install", "-g", f"{PACKAGES['codex']}@latest"]
    return resolve_command("claude") + ["update"]


def failure_hint(text: str) -> str:
    low = text.lower()
    if any(k in low for k in ("ebusy", "eperm", "resource busy", "being used by another process")):
        return "CLI 파일이 사용 중이라 바꾸지 못했습니다. 다른 터미널에서 실행 중인 codex/claude를 모두 닫고 다시 시도하세요."
    if "is not recognized" in low or "내부 또는 외부 명령" in text:
        return "프로그램 경로를 실행하지 못했습니다. Council을 최신 버전으로 업데이트한 뒤 다시 시도하세요."
    if "eacces" in low or "permission denied" in low or "access is denied" in low:
        return "설치 폴더에 쓸 권한이 없습니다. Setup.cmd를 다시 실행하거나 담당자에게 문의하세요."
    if any(k in low for k in ("enotfound", "etimedout", "econnreset", "econnrefused", "network", "getaddrinfo", "unable to connect")):
        return "인터넷 연결 문제로 받지 못했습니다. 회사 네트워크(방화벽)에서 막혔을 수 있습니다."
    return "아래 기록을 확인하세요. 계속 실패하면 Setup.cmd를 다시 실행해 보세요."


def update_cli(name: str) -> dict:
    """CLI 를 최신 버전으로 업데이트한다. 반환: {ok, before, after, latest, output, hint}"""
    if name not in PACKAGES:
        raise ValueError("알 수 없는 CLI 입니다.")
    before = installed_version(name)
    try:
        args = update_args(name)
    except CliFailure as exc:
        return {"ok": False, "before": before, "after": before, "output": "", "hint": str(exc)}
    try:
        proc = subprocess.run(win_cmdline(args), capture_output=True, timeout=UPDATE_TIMEOUT, stdin=subprocess.DEVNULL,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        output = decode_output(proc.stdout) + decode_output(proc.stderr)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        output, code = f"{UPDATE_TIMEOUT // 60}분 안에 끝나지 않아 중단했습니다.", -1
    except OSError as exc:
        output, code = f"실행 실패: {exc}", -1
    with _lock:
        _cache.clear()  # 다음 버전 확인은 새로 조회
    after = installed_version(name)
    latest = latest_version(name)
    ok = code == 0 and bool(after)
    return {
        "ok": ok, "name": NAMES[name], "before": before, "after": after, "latest": latest,
        "output": output.strip()[-3000:], "hint": "" if ok else failure_hint(output),
    }


# ---------- 로그인 창 열기 ----------
LOGIN_RUN = {"codex": ["login"], "claude": ["auth", "login"]}


def open_login(name: str) -> dict:
    """Windows: 로그인 명령이 실행된 터미널 창을 새로 연다 (브라우저 로그인이 이어서 열림).
    그 외 OS: 열 수 없으므로 명령만 돌려준다."""
    if name not in PACKAGES:
        raise ValueError("알 수 없는 CLI 입니다.")
    if os.name != "nt":
        return {"opened": False, "command": LOGIN_COMMANDS[name]}
    import tempfile
    exe = resolve_command(name)[-1]
    lines = [
        "@echo off", "chcp 65001 >nul", f"title {NAMES[name]} 로그인",
        f"echo {NAMES[name]} 로그인을 시작합니다. 브라우저가 열리면 계정으로 로그인하세요.", "echo.",
        f'call "{exe}" {" ".join(LOGIN_RUN[name])}', "echo.",
        "echo 로그인이 끝났으면 이 창을 닫고 AI Council 화면으로 돌아가세요.", "pause",
    ]
    bat = os.path.join(tempfile.gettempdir(), f"ai-council-login-{name}.cmd")
    with open(bat, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write("\n".join(lines) + "\n")
    subprocess.Popen([os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", bat],
                     creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10))
    with _lock:
        for key in [k for k in _cache if k.startswith("login:")]:
            _cache.pop(key, None)
    return {"opened": True, "command": LOGIN_COMMANDS[name]}
