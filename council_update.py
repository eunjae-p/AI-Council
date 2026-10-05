"""AI Council 프로그램 자체 업데이트 (GitHub → 이 PC).

GitHub 저장소가 기준이다. 어느 PC에서 수정하든 GitHub에 올리고, 각 PC는 여기서 받아온다.
안전 규칙
- 대화 기록(data/)·내보내기(exports/)는 .gitignore 대상이라 업데이트가 건드리지 않는다.
- 이 PC에서 코드 파일을 직접 고쳐 GitHub와 내용이 다르면 업데이트하지 않고 파일 목록을 알려준다.
  (내용이 GitHub 최신본과 같으면 기록만 맞춘다: git reset, 파일은 그대로)
- 이 PC에만 있는 커밋이 있으면 업데이트하지 않는다.
- 답변 생성 중에는 업데이트하지 않는다(호출 측에서 확인).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from council_core import ROOT

BRANCH = "main"
_fetch_cache: dict[str, object] = {"time": 0.0, "ok": False, "error": ""}
_lock = threading.Lock()


class UpdateError(RuntimeError):
    pass


def _git(*args: str, timeout: int = 60, check: bool = True) -> subprocess.CompletedProcess:
    exe = shutil.which("git")
    if not exe:
        raise UpdateError("Git이 설치되어 있지 않습니다. Setup.cmd를 다시 실행하거나 https://git-scm.com 에서 설치하세요.")
    proc = subprocess.run(
        [exe, "-C", str(ROOT), *args], capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if check and proc.returncode != 0:
        msg = (proc.stderr or proc.stdout).decode("utf-8", "replace").strip()
        raise UpdateError(f"git {' '.join(args)} 실패: {msg[-800:]}")
    return proc


def _out(*args: str, **kw) -> str:
    return _git(*args, **kw).stdout.decode("utf-8", "replace").strip()


def is_repo() -> bool:
    return (ROOT / ".git").exists()


def file_version(text: str) -> str:
    m = re.search(r'^VERSION\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else ""


def fetch(force: bool = False) -> None:
    with _lock:
        if not force and _fetch_cache["ok"] and time.time() - float(_fetch_cache["time"]) < 600:
            return
        _git("fetch", "--quiet", "origin", BRANCH, timeout=90)
        _fetch_cache.update(time=time.time(), ok=True, error="")


def _norm(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def _differs_from_remote() -> list[str]:
    """작업 폴더의 Git 관리 대상 파일 중 origin/main 과 내용이 다른 파일 목록 (줄바꿈 차이는 무시)."""
    remote_files = set(_out("ls-tree", "-r", "--name-only", f"origin/{BRANCH}").splitlines())
    changed = set()
    status = _git("status", "--porcelain", "--untracked-files=all").stdout.decode("utf-8", "replace")
    for line in status.splitlines():  # 앞 공백이 의미 있으므로 strip 하지 않음
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changed.add(path)
    diff = []
    for path in sorted(changed):
        local = ROOT / path
        if path in remote_files:
            remote = _git("show", f"origin/{BRANCH}:{path}").stdout
            if not local.exists() or _norm(local.read_bytes()) != _norm(remote):
                diff.append(path)
        elif local.exists():  # GitHub 에 없는 새 파일
            diff.append(path)
    return diff


def check(running_version: str, force: bool = False) -> dict:
    if not is_repo():
        return {"status": "not_repo", "message": "Git으로 설치되지 않은 폴더라 자동 업데이트를 할 수 없습니다. "
                "GitHub에서 'git clone'으로 다시 받으면 업데이트 기능을 쓸 수 있습니다.", "running": running_version}
    try:
        fetch(force)
        behind = int(_out("rev-list", "--count", f"HEAD..origin/{BRANCH}") or 0)
        ahead = int(_out("rev-list", "--count", f"origin/{BRANCH}..HEAD") or 0)
        commits = _out("log", "--format=%h %s", f"HEAD..origin/{BRANCH}").splitlines()[:20]
        dirty = bool(_out("status", "--porcelain"))
        remote_version = file_version(_out("show", f"origin/{BRANCH}:ai_council_web.py"))
    except UpdateError as exc:
        return {"status": "error", "message": str(exc), "running": running_version}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "GitHub 연결 시간이 초과되었습니다. 인터넷 연결을 확인하세요.", "running": running_version}
    available = behind > 0 or (remote_version and remote_version != running_version)
    return {
        "status": "available" if available else "latest",
        "running": running_version, "remote": remote_version, "behind": behind, "ahead": ahead,
        "dirty": dirty, "commits": commits,
    }


def apply(running_version: str) -> dict:
    """업데이트 적용. 반환 status: latest | updated | synced. 실패하면 UpdateError."""
    if not is_repo():
        raise UpdateError("Git으로 설치되지 않은 폴더입니다. GitHub에서 git clone으로 다시 받아 주세요.")
    fetch(force=True)
    ahead = int(_out("rev-list", "--count", f"origin/{BRANCH}..HEAD") or 0)
    if ahead:
        raise UpdateError(f"이 PC에 GitHub에 없는 커밋이 {ahead}개 있습니다. 먼저 GitHub에 올리거나 정리한 뒤 업데이트하세요.")
    dirty = bool(_out("status", "--porcelain"))
    before = _out("rev-parse", "--short", "HEAD")
    if dirty:
        diff = _differs_from_remote()
        if diff:
            raise UpdateError("이 PC에서 직접 수정된 파일이 있어 업데이트를 멈췄습니다 (덮어쓰지 않음):\n- "
                              + "\n- ".join(diff[:20]))
        # 파일 내용은 이미 최신본과 같음 → 기록만 맞춘다 (파일은 건드리지 않음)
        _git("reset", "--quiet", f"origin/{BRANCH}")
        # GitHub 에는 있는데 이 PC에 아직 없는 파일만 채운다 (기존 파일은 건드리지 않음)
        missing = [ln[3:].strip().strip('"') for ln in
                   _git("status", "--porcelain").stdout.decode("utf-8", "replace").splitlines() if ln.startswith(" D ")]
        if missing:
            _git("checkout", f"origin/{BRANCH}", "--", *missing)
        status = "synced"
    else:
        behind = int(_out("rev-list", "--count", f"HEAD..origin/{BRANCH}") or 0)
        if not behind:
            new_version = file_version((ROOT / "ai_council_web.py").read_text(encoding="utf-8"))
            return {"status": "latest" if new_version == running_version else "synced",
                    "from": before, "to": before, "version": new_version}
        _git("merge", "--ff-only", "--quiet", f"origin/{BRANCH}")
        status = "updated"
    after = _out("rev-parse", "--short", "HEAD")
    new_version = file_version((ROOT / "ai_council_web.py").read_text(encoding="utf-8"))
    return {"status": status, "from": before, "to": after, "version": new_version}


def restart_detached() -> None:
    """새 서버를 새 창으로 띄운다. 새 서버가 이 서버를 종료시키고 포트를 넘겨받는다."""
    env = dict(os.environ, AI_COUNCIL_NO_BROWSER="1")
    if os.name == "nt":
        subprocess.Popen(
            ["cmd.exe", "/c", str(ROOT / "AI-Council_Web.cmd")], cwd=str(ROOT), env=env,
            creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0x10),
        )
    else:
        subprocess.Popen([sys.executable, str(ROOT / "ai_council_web.py")], cwd=str(ROOT), env=env,
                         start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
