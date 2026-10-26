"""수정 모드: GPT·Claude 가 작업 폴더의 파일을 직접 만들고 고친다 — Git 으로 안전하게.

안전 규칙
- 작업 폴더는 Git 저장소여야 하고, 시작 전에 **변경 사항이 없어야** 한다 (깨끗한 상태).
  → 끝난 뒤 `git diff` 가 곧 "모델이 바꾼 내용"이 되고, 되돌리기가 정확하다.
  → 아니면 사용자가 "저장점 만들기"(git init / 커밋)를 직접 눌러야 진행.
- 수정 권한은 CLI 자체 안전장치 안에서만: Claude 는 파일 편집 자동 승인(acceptEdits, 작업 폴더 안),
  명령 실행(Bash) 도구는 주지 않는다. Codex 는 workspace-write 샌드박스(작업 폴더 안 쓰기, 네트워크 차단).
- 끝나면 바뀐 파일·내용을 화면에 보여 주고, 사용자가 **확정(커밋)** 또는 **되돌리기**를 고른다.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from council_core import decode_output

MAX_DIFF_CHARS = 60_000
COUNCIL_AUTHOR = ["-c", "user.name=AI Council", "-c", "user.email=ai-council@localhost"]


class EditError(RuntimeError):
    pass


def _git(workdir: Path, *args: str, check: bool = True, timeout: int = 60) -> str:
    exe = shutil.which("git")
    if not exe:
        raise EditError("Git이 설치되어 있지 않습니다. 설치 도우미(Setup)를 다시 실행하세요.")
    proc = subprocess.run([exe, "-c", "core.quotepath=false", "-C", str(workdir), *args], capture_output=True, timeout=timeout,
                          stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    out = decode_output(proc.stdout)
    if check and proc.returncode != 0:
        raise EditError(f"git {' '.join(args[:2])} 실패: {decode_output(proc.stderr).strip()[-500:]}")
    return out


def _has_identity(workdir: Path) -> bool:
    return bool(_git(workdir, "config", "user.email", check=False).strip())


def _porcelain(workdir: Path) -> list[tuple[str, str]]:
    out = _git(workdir, "status", "--porcelain", "--untracked-files=all")
    items = []
    for line in out.splitlines():
        if len(line) > 3:
            path = line[3:].strip().strip('"')
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            items.append((line[:2], path))
    return items


def status(workdir: Path) -> dict:
    """{repo: bool, clean: bool, changed: [경로…], root: str}"""
    workdir = Path(workdir)
    root = _git(workdir, "rev-parse", "--show-toplevel", check=False).strip()
    if not root:
        return {"repo": False, "clean": False, "changed": [], "root": ""}
    has_head = bool(_git(workdir, "rev-parse", "--verify", "HEAD", check=False).strip())
    changed = [p for _, p in _porcelain(workdir)]
    return {"repo": True, "clean": not changed and has_head, "changed": changed[:50], "root": root,
            "has_commit": has_head}


def checkpoint(workdir: Path, message: str = "AI Council 수정 전 저장점") -> dict:
    """사용자가 누른 경우에만: Git 저장소가 아니면 만들고, 지금 상태를 커밋해 저장점을 만든다."""
    workdir = Path(workdir)
    if not status(workdir)["repo"]:
        _git(workdir, "init", "-q")
    _git(workdir, "add", "-A")
    author = [] if _has_identity(workdir) else COUNCIL_AUTHOR
    if _git(workdir, "status", "--porcelain").strip() or not status(workdir).get("has_commit"):
        _git(workdir, *author, "commit", "-q", "--allow-empty", "-m", message)
    return status(workdir)


def changes(workdir: Path) -> dict:
    """마지막 커밋(저장점) 이후 바뀐 파일과 내용."""
    workdir = Path(workdir)
    files = []
    for code, path in _porcelain(workdir):
        kind = "new" if code == "??" or "A" in code else "deleted" if "D" in code else "modified"
        files.append({"path": path, "status": kind})
    diff = _git(workdir, "diff", "HEAD", "--no-color", check=False)
    for f in files:  # 새 파일은 diff 에 안 나오므로 내용을 직접 붙인다
        if f["status"] == "new":
            target = workdir / f["path"]
            try:
                text = target.read_text(encoding="utf-8")
                diff += f"\n--- /dev/null\n+++ b/{f['path']}\n" + "".join("+" + ln + "\n" for ln in text.splitlines()[:400])
            except (OSError, UnicodeDecodeError):
                diff += f"\n+++ b/{f['path']} (바이너리 또는 읽을 수 없는 파일)\n"
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + f"\n… (이후 {len(diff) - MAX_DIFF_CHARS:,}자 생략)"
    return {"files": files, "diff": diff}


def revert(workdir: Path, new_files: list[str]) -> None:
    """저장점 상태로 되돌린다: 고친 파일은 원래대로, 새로 만든 파일은 삭제 (모델이 만든 파일만)."""
    workdir = Path(workdir)
    _git(workdir, "restore", "--source=HEAD", "--staged", "--worktree", "--", ".")
    root = workdir.resolve()
    for rel in new_files:
        target = (workdir / rel).resolve()
        if root in target.parents and target.is_file():
            target.unlink()


def commit(workdir: Path, message: str) -> str:
    workdir = Path(workdir)
    _git(workdir, "add", "-A")
    author = [] if _has_identity(workdir) else COUNCIL_AUTHOR
    _git(workdir, *author, "commit", "-q", "-m", message or "AI Council 수정")
    return _git(workdir, "rev-parse", "--short", "HEAD").strip()
