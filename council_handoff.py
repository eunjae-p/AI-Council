"""작업 폴더의 인수인계 기록 (HANDOFF.md) 과 CLAUDE.md 안내.

목적: Council 과 Claude 데스크톱 앱(또는 터미널 Claude Code)이 같은 작업 폴더를 번갈아 쓸 때,
세션(대화)을 넘기지 않고도 "무엇을 했고 무엇이 남았는지"를 이어받게 한다.

- 작업 모드가 끝나면 Council 이 작업 폴더의 HANDOFF.md 맨 아래에 한 항목을 덧붙인다
  (요청 · 실행 모델 · 상태 · 바뀐 파일 · 세션 ID · 결과 요약). 파일을 읽기만 한 질문은 기록하지 않는다.
- CLAUDE.md 에 "작업이 끝나면 HANDOFF.md 에 기록" 규칙을 넣어 두면, 데스크톱 앱에서 한 작업도 같은 파일에 쌓인다.
  Claude Code 는 작업 폴더의 CLAUDE.md 를 자동으로 읽는다 (Council 작업 모드·데스크톱 앱·터미널 모두).
- 파일이 너무 커지면 HANDOFF.old.md 로 옮기고 새로 시작한다 (원문은 지우지 않음).
"""
from __future__ import annotations

import re
import time
from pathlib import Path

HANDOFF_NAME = "HANDOFF.md"
OLD_NAME = "HANDOFF.old.md"
CLAUDE_NAME = "CLAUDE.md"
MAX_BYTES = 200_000
SUMMARY_CHARS = 1500
RULE_MARKER = "<!-- ai-council:handoff -->"
_FILE_TOOLS = re.compile(r"^(Write|Edit|MultiEdit|NotebookEdit): (.+)$")

TEXT = {
    "ko": {
        "title": "# 작업 인수인계 기록 (HANDOFF)\n\n"
                 "AI Council 과 Claude(데스크톱 앱·터미널)가 이 폴더에서 한 작업을 순서대로 남깁니다. "
                 "이어서 작업할 때는 마지막 항목부터 읽으세요.\n",
        "head": "## {time} · {source}",
        "request": "- 요청: {x}",
        "model": "- 실행: {x}",
        "status": "- 상태: {x}",
        "files": "- 바뀐 파일: {x}",
        "session": "- Claude 세션: `{x}` (터미널 `claude --resume {x}` · 데스크톱 앱 `/resume`)",
        "summary": "### 결과 요약",
        "done": "완료", "paused": "⏸ 승인 대기 (허용하면 이어서 진행)", "timeout": "⏱ 시간 제한으로 멈춤 (이어서 진행 가능)",
        "failed": "실패", "unknown": "(확인하지 못함)",
    },
    "en": {
        "title": "# Work handoff log (HANDOFF)\n\n"
                 "AI Council and Claude (desktop app / terminal) record the work done in this folder, in order. "
                 "When you continue, read from the last entry.\n",
        "head": "## {time} · {source}",
        "request": "- Request: {x}",
        "model": "- Ran on: {x}",
        "status": "- Status: {x}",
        "files": "- Changed files: {x}",
        "session": "- Claude session: `{x}` (terminal `claude --resume {x}` · desktop app `/resume`)",
        "summary": "### Result summary",
        "done": "done", "paused": "⏸ waiting for approval (continues after you allow it)",
        "timeout": "⏱ stopped by the time limit (can continue)", "failed": "failed", "unknown": "(not detected)",
    },
}

CLAUDE_RULE = {
    "ko": f"""{RULE_MARKER}
## 작업 인수인계 (AI Council ↔ Claude 데스크톱 앱)
- 작업을 시작할 때 `HANDOFF.md` 가 있으면 마지막 항목부터 읽고 이어서 진행한다.
- 파일을 만들거나 고친 작업이 끝나면 `HANDOFF.md` 맨 아래에 한 항목을 덧붙인다:
  `## 날짜 시각 · Claude 앱` / 요청 / 상태 / 바뀐 파일 / 결과 요약 / 남은 일.
- 기존 항목은 고치거나 지우지 않는다 (덧붙이기만).
""",
    "en": f"""{RULE_MARKER}
## Work handoff (AI Council ↔ Claude desktop app)
- When starting work, if `HANDOFF.md` exists, read it from the last entry and continue from there.
- After work that created or changed files, append one entry at the end of `HANDOFF.md`:
  `## date time · Claude app` / request / status / changed files / result summary / remaining work.
- Never edit or delete existing entries (append only).
""",
}

CLAUDE_TEMPLATE = {
    "ko": """# 프로젝트 안내 (Claude Code 가 자동으로 읽는 파일)

짧게 유지하세요 — 이 파일은 매 작업마다 함께 전달됩니다.

## 프로젝트
- 무엇을 하는 프로젝트인지 한두 줄로:
- 주요 폴더·파일:

## 실행 · 확인 방법
- 실행:
- 테스트:

## 규칙 · 주의
- (예: 운영 중인 서버 파일은 고치기 전에 백업)

""",
    "en": """# Project guide (Claude Code reads this file automatically)

Keep it short — this file is sent with every task.

## Project
- What this project does, in a line or two:
- Main folders/files:

## How to run · check
- Run:
- Test:

## Rules · cautions
- (e.g. back up live server files before changing them)

""",
}


def _lang(lang: str) -> str:
    return "en" if lang == "en" else "ko"


def files_from_activity(items: list[dict]) -> list[str]:
    """Claude 작업 기록(activity)에서 만들거나 고친 파일 경로를 모은다."""
    seen: list[str] = []
    for item in items:
        for act in item.get("activity") or []:
            m = _FILE_TOOLS.match(str(act.get("text", "")))
            if act.get("kind") == "tool" and m and m.group(2) not in seen:
                seen.append(m.group(2))
    return seen


def used_shell(items: list[dict]) -> bool:
    return any(str(a.get("text", "")).startswith("$ ") for it in items for a in it.get("activity") or []
               if a.get("kind") == "tool")


def _rel(path: str, workdir: Path) -> str:
    try:
        return Path(path).resolve().relative_to(workdir.resolve()).as_posix()
    except (ValueError, OSError):
        return path


def append_entry(workdir: Path, lang: str, question: str, items: list[dict], changed: list[str] | None = None,
                 source: str = "AI Council") -> Path:
    """HANDOFF.md 에 한 항목을 덧붙인다. items: 이번 질문에서 작업 모드로 나온 답변들 (마지막이 최종 보고)."""
    t = TEXT[_lang(lang)]
    workdir = Path(workdir)
    path = workdir / HANDOFF_NAME
    if path.exists() and path.stat().st_size > MAX_BYTES:
        old = workdir / OLD_NAME
        with old.open("a", encoding="utf-8") as out:  # 이전 기록은 지우지 않고 옮겨 둔다
            out.write(path.read_text(encoding="utf-8", errors="replace"))
        path.unlink()
    last = items[-1] if items else {}
    models = []
    for it in items:
        name = str(it.get("model") or "")
        if name and name not in models:
            models.append(name)
    status = t["timeout"] if last.get("paused") == "timeout" else t["paused"] if last.get("paused") else t["done"]
    files = [_rel(f, workdir) for f in (changed or files_from_activity(items))]
    files = [f for f in files if f not in (HANDOFF_NAME, OLD_NAME)]
    session = next((str(it["claude_session"]) for it in reversed(items) if it.get("claude_session")), "")
    body = str(last.get("content") or "").strip()
    if len(body) > SUMMARY_CHARS:
        body = "…" + body[-SUMMARY_CHARS:]
    # 답변 안의 제목(#, ##)이 항목 제목(##)처럼 보이지 않게 한 단계 아래로
    body = re.sub(r"(?m)^#{1,3}(?=\s)", "####", body)
    one_line = " ".join(str(question).split())
    lines = [
        "",
        t["head"].format(time=time.strftime("%Y-%m-%d %H:%M"), source=source),
        t["request"].format(x=one_line[:300] + ("…" if len(one_line) > 300 else "")),
        t["model"].format(x=", ".join(models) or "-"),
        t["status"].format(x=status),
        t["files"].format(x=", ".join(files[:30]) + (" …" if len(files) > 30 else "") if files else t["unknown"]),
    ]
    if session:
        lines.append(t["session"].format(x=session))
    if body and body != "…":
        lines += ["", t["summary"], body]
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="\n") as out:
        if new:
            out.write(t["title"])
        out.write("\n".join(lines) + "\n")
    return path


def setup(workdir: Path, lang: str) -> dict:
    """CLAUDE.md 가 없으면 틀을 만들고, 있으면 인수인계 규칙만 (없을 때) 덧붙인다."""
    l = _lang(lang)
    path = Path(workdir) / CLAUDE_NAME
    if not path.exists():
        path.write_text(CLAUDE_TEMPLATE[l] + CLAUDE_RULE[l], encoding="utf-8", newline="\n")
        return {"path": str(path), "created": True, "updated": False}
    text = path.read_text(encoding="utf-8", errors="replace")
    if RULE_MARKER in text:
        return {"path": str(path), "created": False, "updated": False}
    with path.open("a", encoding="utf-8", newline="\n") as out:
        out.write(("" if text.endswith("\n") else "\n") + "\n" + CLAUDE_RULE[l])
    return {"path": str(path), "created": False, "updated": True}


def status(workdir: Path) -> dict:
    p = Path(workdir)
    claude = p / CLAUDE_NAME
    has_rule = False
    if claude.exists():
        try:
            has_rule = RULE_MARKER in claude.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return {"claude_md": claude.exists(), "rule": has_rule, "handoff": (p / HANDOFF_NAME).exists()}
