"""MCP(연결된 외부 도구) 사용 — 승인 기반.

원칙
- 기본은 꺼짐. 켜도 **사용자가 허용한 도구만** 승인 없이 실행된다 (Claude Code 의 --allowedTools).
- 허용하지 않은 도구를 모델이 쓰려 하면 CLI 가 실행을 거부하고(permission_denials), Council 이 화면에
  "이 도구를 쓰려 합니다 — 허용/거부"를 보여 준다. 사용자가 허용하면 그 도구를 열고 다시 답하게 한다.
- 모든 도구를 묻지 않고 실행하는 모드(bypassPermissions)는 쓰지 않는다.
- 현재는 Claude(Claude Code) 의 MCP 만 지원. Claude Code 는 claude.ai 계정에 연결된 커넥터도 불러온다.
  GPT(Codex) 쪽 MCP 는 승인 흐름을 확인하기 전까지 Council 에서 끈다.

저장 (Git 제외)
- data/mcp_state.json    : 마지막으로 확인한 서버·도구 목록
- data/mcp_settings.json : 사용자가 "항상 허용"한 도구 목록
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

from council_core import CliFailure, chat_dir, resolve_command, win_cmdline

DISCOVER_TIMEOUT = 90
_lock = threading.Lock()
_TOOL_RE = re.compile(r"^mcp__[A-Za-z0-9_.-]+$")

# 이름으로 대략 분류 (참고용 표시 — 허용 여부는 항상 사용자가 정한다)
_READ_WORDS = ("get", "list", "show", "search", "read", "fetch", "query", "find", "view", "status", "balance",
               "transactions", "describe", "info", "explore", "wait", "check")
_ACTION_WORDS = ("generate", "create", "add", "update", "delete", "remove", "send", "post", "publish", "upload",
                 "write", "edit", "move", "deploy", "execute", "run", "buy", "purchase", "cancel", "invoke",
                 "import", "build", "participate", "connect", "reframe", "upscale", "outpaint", "dubbing")


def split_name(tool: str) -> tuple[str, str]:
    """mcp__서버__도구 → (서버, 도구)"""
    body = tool[len("mcp__"):] if tool.startswith("mcp__") else tool
    server, _, name = body.partition("__")
    return server, name or body


def classify(tool: str) -> str:
    """'read'(조회로 보임) | 'action'(생성·수정·비용 가능) | 'unknown'"""
    name = split_name(tool)[1].lower()
    words = re.split(r"[_\-.]", name)
    if any(w in _ACTION_WORDS for w in words):
        return "action"
    if any(w in _READ_WORDS for w in words):
        return "read"
    return "unknown"


def valid_tool(tool: object) -> bool:
    return isinstance(tool, str) and bool(_TOOL_RE.match(tool)) and len(tool) <= 200


class McpStore:
    def __init__(self, data_dir: Path):
        self.state_path = Path(data_dir) / "mcp_state.json"
        self.settings_path = Path(data_dir) / "mcp_settings.json"

    @staticmethod
    def _load(path: Path) -> dict:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _save(path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)

    def allowed(self) -> list[str]:
        return [t for t in self._load(self.settings_path).get("allowed", []) if valid_tool(t)]

    def set_allowed(self, tool: str, allow: bool) -> list[str]:
        if not valid_tool(tool):
            raise ValueError("도구 이름이 올바르지 않습니다.")
        with _lock:
            data = self._load(self.settings_path)
            current = [t for t in data.get("allowed", []) if valid_tool(t)]
            if allow and tool not in current:
                current.append(tool)
            if not allow:
                current = [t for t in current if t != tool]
            data["allowed"] = sorted(current)
            self._save(self.settings_path, data)
            return data["allowed"]

    def state(self) -> dict:
        state = self._load(self.state_path)
        allowed = set(self.allowed())
        tools = [{"name": t, "server": split_name(t)[0], "tool": split_name(t)[1], "kind": classify(t),
                  "allowed": t in allowed} for t in state.get("tools", []) if valid_tool(t)]
        return {"checked_at": state.get("checked_at"), "servers": state.get("servers", []), "tools": tools,
                "allowed": sorted(allowed), "error": state.get("error", "")}

    def refresh(self) -> dict:
        """Claude Code 를 잠깐 실행해 시작 정보(init)에서 MCP 서버·도구 목록만 읽고 바로 종료한다.
        모델이 답을 만들기 전에 끝내므로 사용량은 거의 들지 않는다."""
        try:
            servers, tools = discover_claude()
            data = {"checked_at": time.time(), "servers": servers, "tools": tools, "error": ""}
        except CliFailure as exc:
            data = {**self._load(self.state_path), "checked_at": time.time(), "error": str(exc)}
        with _lock:
            self._save(self.state_path, data)
        return self.state()


def discover_claude() -> tuple[list[dict], list[str]]:
    command = resolve_command("claude") + [
        "-p", "--no-session-persistence", "--output-format", "stream-json", "--verbose", "--tools", "",
    ]  # 시작 정보(init)를 받는 즉시 종료하므로 도구는 실행되지 않는다
    process = subprocess.Popen(win_cmdline(command), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               cwd=str(chat_dir()), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    result: dict = {}

    def reader() -> None:
        assert process.stdout is not None
        for raw in process.stdout:
            try:
                msg = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if isinstance(msg, dict) and msg.get("type") == "system" and msg.get("subtype") == "init":
                result["init"] = msg
                return

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    try:
        assert process.stdin is not None
        process.stdin.write(b"Reply with OK.")
        process.stdin.close()
    except OSError:
        pass
    thread.join(DISCOVER_TIMEOUT)
    from council_core import _kill_tree
    _kill_tree(process)  # 시작 정보만 필요하므로 모델 답변 전에 종료
    init = result.get("init")
    if not init:
        err = b""
        try:
            err = process.stderr.read() if process.stderr else b""
        except (OSError, ValueError):
            pass
        raise CliFailure("claude", "MCP 목록을 가져오지 못했습니다. Claude 로그인 상태와 CLI 버전을 확인하세요.",
                         "", err.decode("utf-8", "replace")[-1500:])
    tools = sorted({t for t in init.get("tools", []) if isinstance(t, str) and t.startswith("mcp__")})
    servers = [{"name": str(s.get("name", "")), "status": str(s.get("status", ""))}
               for s in init.get("mcp_servers", []) if isinstance(s, dict)]
    return servers, tools
