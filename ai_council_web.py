"""AI Council 로컬 웹 서버 (V0.6).

Codex CLI와 Claude Code CLI를 구독 계정으로 호출하는 로컬 멀티모델 채팅 앱.
Python 표준 라이브러리만 사용한다. API 키를 사용하지 않는다.
"""
from __future__ import annotations

import json
import os
import random
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from council_context import build_context, maybe_summarize
from council_core import (
    TIMEOUT_SECONDS,
    Cancelled,
    CancelToken,
    MODES,
    FOLDER_MODES,
    ACCOUNT_DEFAULT,
    actual_model,
    call_model,
    check_workdir,
    codex_default_model,
    ROOT,
    SETUP_NAME,
    CliFailure,
    claude_args,
    codex_args,
    resolve_command,
    run_cli,
)
from council_store import ConversationStore
import council_debate as debate
import council_edit
import council_i18n
import council_versions
import council_attach
import council_media
import council_update
from council_state import CliState
from council_mcp import McpStore, valid_tool
import council_commands

VERSION = "0.17.0"
HOST = "127.0.0.1"
PORT = 8765
INDEX = ROOT / "web" / "index.html"
MAX_BODY = 12_000_000
ATTACH_TIMEOUT = 300  # 첨부·작업 모드는 분석량이 많아 제한 시간을 늘림
WEB_TIMEOUT = 480     # 웹 검색을 켜면 검색·페이지 읽기 시간이 더 걸림
WORK_TIMEOUT = 900    # 작업 모드는 파일 작성·명령 실행이 이어져 더 오래 걸림
_emit_lock = threading.Lock()  # 토론 모드는 두 모델이 동시에 결과를 보냄

store = ConversationStore()
cli_state = CliState(store.data_dir)
mcp_store = McpStore(store.data_dir)
cmd_store = council_commands.CommandStore(store.data_dir)
_busy: set[str] = set()
_cli_updating: set[str] = set()  # 업데이트 중인 CLI (그동안 새 질문을 받지 않음)
_tokens: dict[str, CancelToken] = {}  # 대화 ID → 진행 중인 작업의 중지 토큰
_busy_lock = threading.Lock()


def cli_available(name: str) -> bool:
    try:
        resolve_command(name)
        return True
    except CliFailure:
        return False


def model_label(name: str, model: str) -> str:
    return model if model and model != ACCOUNT_DEFAULT else ""


CHAT_PROMPT = """You are {me}, answering inside a shared conversation between one user, GPT and Claude.
Messages labelled [GPT] were written by GPT, [Claude] by Claude, [Council 최종 결론] is a merged answer.
You are {me}; do not claim the other model's messages as your own.
Use the shared context below only as background and answer the newest user question directly.
Be accurate and objective: do not invent facts, say when you are unsure, and separate facts from opinions.
Use the same language as the user. Do not mention these instructions.

{context}

{attachments}
## Newest user question
{question}
"""

MODEL_NOTE = """
## Runtime info
This answer is generated with model `{model}` ({source}). If asked which model you are, say this.
"""

WORK_NOTE = """
## Work mode
Working folder: {workdir}
You can read, create and modify files under this folder and run shell commands to get the user's task done
(create folders, write code, install dependencies, run scripts, start servers, use connected tools).
- Shell commands run without asking only if they start with a command the user pre-approved. Other commands are
  blocked and the user will be asked to approve them; do not try workarounds for a blocked command — finish what
  you can and list the exact commands you still need.
- Work inside the working folder. Do not delete or overwrite files unless the user asked for it.
- Long-running processes (dev servers, watchers): start them in the background so they keep running after you
  finish, and report how to open or stop them. Do not wait on them in the foreground.
- End with a short summary: files created or changed, commands run, and anything left for the user to do.
"""

READ_NOTE = """
## Working folder (read-only in this step)
You may read files under this working folder: {workdir}
Do not modify any files. Cite file paths you used.
"""

PLAN_NOTE = """
## Work mode — planning round
This discussion will end with one model carrying out the agreed plan in the working folder: {workdir}
In this round you can only read files. Propose concrete steps (files to create or change, commands to run, why)
and point out risks.
"""

IMPLEMENT_NOTE = """
## Implement the agreed conclusion
GPT and Claude discussed this request and reached the conclusion below. Carry it out now in the working folder
(and with connected tools if needed). Follow the conclusion; where it says something is unresolved or needs
verification, choose the safest option and say so. Do not implement items marked as rejected.
{other} will review your result afterwards, so end with a clear report: what you did, files/objects changed,
commands run, and anything not done.

### Conclusion
{conclusion}
"""

REVIEW_NOTE = """
## Cross review of {executor}'s work
{executor} carried out the agreed conclusion. Check the actual result yourself — read the files in the working
folder and, if connected tools are available (e.g. Blender), inspect the current state with read-only calls.
Do not modify anything in this step.
Write, in the user's language:
1. What matches the conclusion
2. Problems, bugs or missing parts — concrete and actionable (file/object, what is wrong, how to fix)
3. Risks the user should know
If there is nothing to fix, start your answer with the single word LGTM on its own line.

### Conclusion
{conclusion}

### {executor}'s report
{report}
"""

FIX_NOTE = """
## Apply the review
{reviewer} reviewed your work and reported the issues below. Fix the valid ones now in the working folder (and with
connected tools if needed). If you disagree with a point, say why instead of changing it. End with a short report.

### Review
{review}
"""

SYNTH_PROMPT = """Create one final answer for the user from the two answers below.
Resolve disagreements (say briefly which view is better supported and why), keep useful details,
and output only the final answer. Use the user's language.

Shared context:
{context}

User question:
{question}

Attached file summaries:
{attachments}

GPT answer:
{gpt}

Claude answer:
{claude}
"""


class Handler(BaseHTTPRequestHandler):
    server_version = f"AI-Council/{VERSION}"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    # ---------- 공통 ----------
    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > MAX_BODY:
            raise ValueError("요청이 너무 큽니다.")
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        body = json.loads(raw or "{}")
        if not isinstance(body, dict):
            raise ValueError("잘못된 요청입니다.")
        return body

    @property
    def lang(self) -> str:
        """화면 언어 (브라우저가 X-Lang 헤더로 알려 줌). 안내·오류 문구를 내보내기 직전에 번역한다."""
        return council_i18n.request_lang(self.headers)

    def send_json(self, value: object, status: int = 200) -> None:
        value = council_i18n.localize(value, self.lang)
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass  # 브라우저가 먼저 페이지를 떠난 경우

    def start_stream(self) -> None:
        self.stream_alive = True
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

    def emit(self, kind: str, **payload: object) -> None:
        # 브라우저가 끊겨도 작업과 저장은 끝까지 진행한다.
        if kind == "stage":
            self.last_stage = str(payload.get("text", ""))
        if not getattr(self, "stream_alive", False):
            return
        line = json.dumps(council_i18n.localize({"type": kind, **payload}, self.lang), ensure_ascii=False) + "\n"
        with _emit_lock:
            try:
                self.wfile.write(line.encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                self.stream_alive = False

    # ---------- GET ----------
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        arg = lambda key: query.get(key, [""])[0]  # noqa: E731
        try:
            if parsed.path == "/":
                content = INDEX.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(content)
            elif parsed.path == "/api/status":
                self.send_json({
                    "ok": True, "version": VERSION, "model": ACCOUNT_DEFAULT,
                    "cli": {"codex": cli_available("codex"), "claude": cli_available("claude")},
                    "ffmpeg": council_media.ffmpeg_available(),
                    "default_models": cli_state.defaults(), "usage": cli_state.usage(),
                    "platform": "windows" if os.name == "nt" else ("mac" if sys.platform == "darwin" else "linux"),
                    "setup": SETUP_NAME,
                })
            elif parsed.path == "/api/attachment":
                self.send_attachment(arg("conversation_id"), arg("file"))
                return
            elif parsed.path == "/api/update/check":
                self.send_json(council_update.check(VERSION, force=arg("refresh") == "1"))
            elif parsed.path == "/api/commands":
                self.send_json(cmd_store.state())
            elif parsed.path == "/api/mcp":
                self.send_json(mcp_store.state())
            elif parsed.path == "/api/versions":
                self.send_json(council_versions.check(force=arg("refresh") == "1"))
            elif parsed.path == "/api/conversations":
                scope = arg("scope") or "all"
                if scope not in {"all", "active", "archived", "trash"}:
                    raise ValueError("잘못된 목록 범위입니다.")
                self.send_json({"items": store.list(scope)})
            elif parsed.path == "/api/conversation":
                self.send_json(store.detail(store.check_id(arg("id"))))
            elif parsed.path == "/api/history":  # V0.5 호환
                self.send_json({"items": store.load_messages(store.check_id(arg("conversation_id")))})
            elif parsed.path == "/api/search":
                q = arg("q").strip()
                if not q:
                    self.send_json({"items": [], "query": ""})
                else:
                    self.send_json({"items": store.search(q[:200]), "query": q})
            else:
                self.send_error(404)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)

    # ---------- POST ----------
    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/chat":
            self.handle_chat()
            return
        if path == "/api/debate":  # V0.4 자동 토론 API 는 토론 모드(target=both)로 대체됨
            self.send_json({"error": "이 API는 더 이상 쓰지 않습니다. /api/chat 에 target=both(토론)를 사용하세요."}, 410)
            return
        if path == "/api/upload":
            self.handle_upload()
            return
        try:
            body = self.read_json()
            cid = lambda: store.check_id(str(body.get("id") or body.get("conversation_id") or ""))  # noqa: E731
            if path == "/api/conversations":
                self.send_json({"id": (meta := store.create())["id"], "meta": store._public_meta(meta)})
            elif path == "/api/update/apply":
                with _busy_lock:
                    if _busy:
                        raise RuntimeError("답변을 생성하는 중에는 업데이트할 수 없습니다. 완료되거나 중지한 뒤 다시 시도하세요.")
                try:
                    result = council_update.apply(VERSION)
                except council_update.UpdateError as exc:
                    self.send_json({"error": str(exc)}, 409)
                    return
                restart = result["status"] == "updated" or result.get("version") != VERSION
                result["restarting"] = restart
                self.send_json(result)
                if restart:  # 새 서버가 뜨면서 이 서버를 종료시키고 포트를 넘겨받는다
                    threading.Timer(0.5, council_update.restart_detached).start()
            elif path == "/api/cli/update":
                name = str(body.get("name", ""))
                if name not in ("codex", "claude"):
                    raise ValueError("알 수 없는 CLI 입니다.")
                with _busy_lock:
                    if _busy:
                        raise RuntimeError("답변을 생성하는 중에는 업데이트할 수 없습니다. 완료되거나 중지한 뒤 다시 시도하세요.")
                    if _cli_updating:
                        raise RuntimeError("이미 업데이트가 진행 중입니다. 잠시 기다려 주세요.")
                    _cli_updating.add(name)
                try:
                    self.send_json(council_versions.update_cli(name))
                finally:
                    with _busy_lock:
                        _cli_updating.discard(name)
            elif path == "/api/debate/open":
                # 토론 기록 폴더를 탐색기로 연다 (data/debates 아래만)
                rel = str(body.get("dir", "")).replace("\\", "/")
                base = (store.data_dir / "debates").resolve()
                target = (store.data_dir / rel).resolve()
                if not rel.startswith("debates/") or base not in target.parents or not target.is_dir():
                    raise ValueError("토론 기록 폴더를 찾을 수 없습니다.")
                opened = False
                if os.name == "nt":
                    os.startfile(str(target))  # noqa: S606 — 로컬 탐색기 열기
                    opened = True
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(target)])  # Finder 로 열기
                    opened = True
                self.send_json({"opened": opened, "path": str(target)})
            elif path == "/api/edit/status":
                self.send_json(council_edit.status(check_workdir(str(body.get("workdir", "")))))
            elif path == "/api/edit/checkpoint":
                self.send_json(council_edit.checkpoint(check_workdir(str(body.get("workdir", "")))))
            elif path == "/api/edit/apply":
                # 수정 결과 확정(커밋) 또는 되돌리기 — 사용자가 화면에서 누른 경우에만
                conversation_id = cid()
                self.ensure_idle(conversation_id)
                ref, action = str(body.get("ref", "")), str(body.get("action", ""))
                if action not in ("commit", "revert"):
                    raise ValueError("알 수 없는 작업입니다.")
                items = store.load_messages(conversation_id)
                rec = next((i for i in items if i.get("id") == ref and i.get("role") == "edit" and i.get("action") == "pending"), None)
                if rec is None:
                    raise ValueError("변경 기록을 찾을 수 없습니다.")
                if any(i.get("role") == "edit" and i.get("ref") == ref for i in items):
                    raise RuntimeError("이미 확정하거나 되돌린 변경입니다.")
                folder = check_workdir(rec["workdir"])
                if action == "commit":
                    head = council_edit.commit(folder, str(body.get("message") or "")[:200] or f"AI Council: {rec['content'][:80]}")
                    text = f"변경을 확정했습니다 (커밋 {head})."
                else:
                    council_edit.revert(folder, [f["path"] for f in rec.get("files", []) if f.get("status") == "new"])
                    text = "변경을 되돌렸습니다 (수정 전 상태로 복구)."
                done = store.append_message(conversation_id, "edit", text, "변경", ref=ref, action=action)
                self.send_json({"ok": True, "item": done})
            elif path == "/api/commands/allow":
                prefix = str(body.get("prefix", "")).strip()
                if not council_commands.valid_prefix(prefix):
                    raise ValueError("명령 접두어가 올바르지 않습니다.")
                cmd_store.set_allowed(prefix, bool(body.get("allowed", True)))
                self.send_json(cmd_store.state())
            elif path == "/api/commands/reset":
                cmd_store.reset()
                self.send_json(cmd_store.state())
            elif path == "/api/mcp/refresh":
                self.send_json(mcp_store.refresh())
            elif path == "/api/mcp/allow":
                tool = body.get("tool")
                if not valid_tool(tool):
                    raise ValueError("도구 이름이 올바르지 않습니다.")
                mcp_store.set_allowed(tool, bool(body.get("allowed", True)))
                self.send_json(mcp_store.state())
            elif path == "/api/cli/login":
                name = str(body.get("name", ""))
                if name not in ("codex", "claude"):
                    raise ValueError("알 수 없는 CLI 입니다.")
                self.send_json(council_versions.open_login(name))
            elif path == "/api/chat/stop":
                with _busy_lock:
                    tok = _tokens.get(cid())
                if tok is None:
                    self.send_json({"ok": False, "message": "진행 중인 답변이 없습니다."})
                else:
                    tok.reason = {"esc": "Esc 키", "button": "■ 중지 버튼"}.get(str(body.get("reason")), "중지 요청")
                    tok.cancel()
                    self.send_json({"ok": True})
            elif path == "/api/conversation/rename":
                self.send_json({"meta": store.rename(cid(), str(body.get("title", "")))})
            elif path == "/api/conversation/archive":
                self.send_json({"meta": store.set_archived(cid(), bool(body.get("archived", True)))})
            elif path == "/api/conversation/delete":
                conversation_id = cid()
                self.ensure_idle(conversation_id)
                store.delete(conversation_id)
                self.send_json({"ok": True})
            elif path == "/api/conversation/restore":
                self.send_json({"meta": store.restore(cid())})
            elif path == "/api/conversation/purge":
                store.purge(cid())
                self.send_json({"ok": True})
            elif path == "/api/history/clear":
                conversation_id = cid()
                self.ensure_idle(conversation_id)
                self.send_json({"ok": True, "backup": store.clear(conversation_id)})
            elif path == "/api/conversation/summarize":
                conversation_id = cid()
                self.ensure_idle(conversation_id)
                prefer = "gpt" if body.get("prefer") == "gpt" else "claude"
                result = maybe_summarize(store, conversation_id, prefer, force=True)
                self.send_json({"result": result, "meta": store.detail(conversation_id)["meta"]})
            elif path == "/api/export":
                file_path, markdown = store.export_markdown(cid(), lang=self.lang)
                self.send_json({"path": str(file_path), "filename": file_path.name, "markdown": markdown})
            elif path == "/api/shutdown":
                self.send_json({"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                self.send_error(404)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except council_edit.EditError as exc:
            self.send_json({"error": str(exc)}, 409)
        except RuntimeError as exc:
            self.send_json({"error": str(exc)}, 409)
        except (OSError, json.JSONDecodeError) as exc:
            self.send_json({"error": f"처리 실패: {exc}"}, 500)

    def handle_upload(self) -> None:
        """이미지·영상 원본 업로드 (본문 = 파일 바이트). 쿼리: conversation_id, name"""
        query = parse_qs(urlparse(self.path).query)
        try:
            conversation_id = store.check_id(query.get("conversation_id", [""])[0])
            if not store.exists(conversation_id):
                raise ValueError("대화를 찾을 수 없습니다.")
            length = int(self.headers.get("Content-Length", "0") or 0)
            info = council_attach.save_upload(store.data_dir, conversation_id,
                                              query.get("name", ["file"])[0], self.rfile, length)
        except ValueError as exc:
            self.close_connection = True  # 남은 본문을 읽지 않았으므로 연결을 닫는다
            self.send_json({"error": str(exc)}, 400)
            return
        except OSError as exc:
            self.close_connection = True
            self.send_json({"error": f"저장 실패: {exc}"}, 500)
            return
        self.send_json(info)

    def send_attachment(self, conversation_id: str, rel: str) -> None:
        """대화에 첨부된 이미지·영상 프레임을 화면에 보여주기 위한 읽기 전용 엔드포인트."""
        try:
            base = council_attach.attach_dir(store.data_dir, store.check_id(conversation_id)).resolve()
            path = (base / rel).resolve()
            if base not in path.parents or not path.is_file():
                raise ValueError
        except ValueError:
            self.send_error(404)
            return
        ctype = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
                 ".gif": "image/gif", ".bmp": "image/bmp", ".mp4": "video/mp4", ".webm": "video/webm",
                 ".mov": "video/quicktime"}.get(path.suffix.lower(), "application/octet-stream")
        size = path.stat().st_size
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "private, max-age=3600")
        self.end_headers()
        try:
            with path.open("rb") as fh:
                while chunk := fh.read(1024 * 1024):
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    @staticmethod
    def ensure_idle(conversation_id: str) -> None:
        with _busy_lock:
            if conversation_id in _busy:
                raise RuntimeError("이 대화는 답변을 생성하는 중입니다. 완료 후 다시 시도하세요.")

    # ---------- 채팅 ----------
    def handle_chat(self) -> None:
        try:
            body = self.read_json()
            question = str(body.get("question", "")).strip()
            target = str(body.get("target", "both")).strip().lower()
            gpt_model = str(body.get("gpt_model", "")).strip()[:100]
            claude_model = str(body.get("claude_model", "")).strip()[:100]
            conversation_id = store.check_id(str(body.get("conversation_id", "")).strip())
            if not store.exists(conversation_id):
                raise ValueError("대화를 찾을 수 없습니다. 목록을 새로고침하세요.")
            mode = str(body.get("mode", "chat")).strip().lower()
            if mode not in MODES or mode == "read":
                raise ValueError("지원하지 않는 모드입니다.")
            if mode == "edit":
                mode = "work"  # 예전 수정 모드 = 작업 모드
            workdir = check_workdir(str(body.get("workdir", ""))) if mode in FOLDER_MODES else None
            files = council_attach.validate(body.get("attachments"), store.data_dir, conversation_id)
            web = bool(body.get("web"))
            mcp = bool(body.get("mcp_claude", body.get("mcp")))  # Claude MCP (예전 이름: mcp)
            mcp_gpt = bool(body.get("mcp_gpt"))                     # GPT(Codex) MCP
            executor = "gpt" if str(body.get("executor", "")).lower() == "gpt" else "claude"  # 토론+작업에서 실행할 모델
            allow_once = [t for t in body.get("allow_once") or [] if valid_tool(t)][:20] if mcp else []
            cmd_once = [c.strip() for c in body.get("allow_cmds_once") or []
                        if council_commands.valid_prefix(c)][:20] if mode == "work" else []
            if not question and files:
                question = "첨부한 파일을 분석해줘."
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc) or "잘못된 요청입니다."}, 400)
            return
        if not question:
            self.send_json({"error": "질문을 입력하세요."}, 400)
            return
        if target not in {"gpt", "claude", "both"}:
            self.send_json({"error": "지원하지 않는 답변 모델입니다."}, 400)
            return
        with _busy_lock:
            if _cli_updating:
                self.send_json({"error": "GPT/Claude 프로그램을 업데이트하는 중입니다. 끝난 뒤 다시 보내 주세요."}, 409)
                return
            if conversation_id in _busy:
                self.send_json({"error": "이 대화는 이미 답변을 생성하는 중입니다."}, 409)
                return
            _busy.add(conversation_id)
            self.cancel = _tokens[conversation_id] = CancelToken()
        try:
            self.start_stream()
            try:
                self.run_chat(conversation_id, question, target, gpt_model, claude_model, mode, workdir, files, web,
                              mcp, allow_once, cmd_once, mcp_gpt, executor)
            except Exception as exc:  # 예상 못 한 오류도 화면에 정확히 보이게
                self.emit("error", text=f"서버 내부 오류: {type(exc).__name__}: {exc}")
        finally:
            with _busy_lock:
                _busy.discard(conversation_id)
                _tokens.pop(conversation_id, None)

    def run_chat(self, conversation_id: str, question: str, target: str, gpt_model: str, claude_model: str,
                 mode: str = "chat", workdir=None, files: list | None = None, web: bool = False,
                 mcp: bool = False, allow_once: list | None = None, cmd_once: list | None = None,
                 mcp_gpt: bool = False, executor: str = "claude") -> None:
        # 1) 필요할 때만 장기 요약 갱신 (실패해도 채팅은 계속)
        started_at = time.time()
        self.emit("stage", step=0, text="대화 맥락을 준비하는 중")
        prefer = "gpt" if target == "gpt" else "claude"
        token = getattr(self, "cancel", None) or CancelToken()
        result = maybe_summarize(store, conversation_id, prefer, gpt_model, claude_model, cancel=token)
        if result["status"] == "updated":
            self.emit("summary", text=f"오래된 대화를 장기 요약으로 정리했습니다 ({result['model']}).")
        elif result["status"] == "failed":
            self.emit("warning", text="장기 요약 갱신에 실패했습니다. 원문은 그대로이며 최근 대화만으로 답변합니다.\n" + result["error"][:800])

        # 2) 컨텍스트는 질문 저장 전에 만든다 (질문은 별도 섹션으로 전달)
        context, info = build_context(store, conversation_id)
        attached = []
        previous = store.load_messages(conversation_id)
        if files:
            has_video = any(f.get("kind") == "video" for f in files)
            self.emit("stage", step=0, text="영상에서 프레임을 뽑는 중" if has_video else "첨부 파일을 분석하는 중")
            attached = council_attach.process(files, store.data_dir, conversation_id)
        attach_block = council_attach.prompt_block(attached)
        images = council_attach.images_for(attached)
        if not images:  # 새 이미지가 없으면 최근에 첨부한 이미지·영상 프레임을 다시 보여준다
            resent = council_attach.recent_media(previous)
            if resent:
                images = council_attach.images_for(resent)
                attach_block += council_attach.prompt_block(resent, resent=True)
        image_dir = council_attach.attach_dir(store.data_dir, conversation_id) if images else None
        failed_media = [it for it in attached if it.get("error")]
        if failed_media:
            # 영상을 못 읽었는데 모델을 부르면 사용량만 쓰고 "못 봤다"는 답만 온다 → 여기서 멈춘다
            text = "영상 분석을 준비하지 못해 모델에 보내지 않았습니다.\n\n" + "\n".join(
                f"- {it['name']}: {it['error']}" for it in failed_media)
            user_item = store.append_message(conversation_id, "user", question, "사용자", target=target,
                                             mode=mode, workdir=str(workdir) if workdir else None,
                                             attachments=council_attach.history_records(attached) or None)
            self.emit("saved", item=user_item, context=info)
            store.append_message(conversation_id, "error", text, "오류", failed_message_id=user_item["id"])
            self.emit("error", text=text)
            self.emit("done", meta=store.detail(conversation_id)["meta"], errors={})
            return
        timeout = ATTACH_TIMEOUT if (attached or images or mode in FOLDER_MODES) else TIMEOUT_SECONDS
        if mode == "work":
            timeout = max(timeout, WORK_TIMEOUT)
        if web or mcp or mcp_gpt:
            timeout = max(timeout, WEB_TIMEOUT)
        # MCP: 사용자가 "항상 허용"한 도구 + 이번 질문에서만 허용한 도구
        mcp_allow = sorted(set(mcp_store.allowed()) | set(allow_once or [])) if mcp else None
        # 작업 모드 명령: 허용 목록 + 이번 질문에서만 허용한 명령 접두어
        cmd_allow = sorted(set(cmd_store.allowed()) | set(cmd_once or [])) if mode == "work" else None
        # 작업 폴더가 깨끗한 Git 저장소면 끝난 뒤 바뀐 파일을 보여 주고 확정/되돌리기 (아니면 건너뜀)
        track_git = False
        if mode == "work":
            try:
                st = council_edit.status(workdir)
                track_git = bool(st["repo"] and st["clean"])
            except council_edit.EditError:
                track_git = False
        user_item = store.append_message(conversation_id, "user", question, "사용자", target=target,
                                         mode=mode, workdir=str(workdir) if workdir else None, web=web or None,
                                         mcp=mcp or None, mcp_gpt=mcp_gpt or None, allow_once=allow_once or None,
                                         executor=executor if (mode == "work" and target == "both") else None,
                                         allow_cmds_once=cmd_once or None,
                                         attachments=council_attach.history_records(attached) or None)
        self.emit("saved", item=user_item, context=info)

        models = {"gpt": ("GPT", "codex", gpt_model), "claude": ("Claude", "claude", claude_model)}
        answers: dict[str, str] = {}
        errors: dict[str, str] = {}
        stopped = token.cancelled
        discussion = target == "both"

        def base_prompt(which: str, phase: str = "") -> str:
            label, name, model = models[which]
            prompt = CHAT_PROMPT.format(me=label, context=context, question=question, attachments=attach_block)
            if mode == "work":
                note = PLAN_NOTE if phase == "plan" else READ_NOTE if phase == "review" else WORK_NOTE
                prompt += note.format(workdir=workdir)
            selected = model_label(name, model) or (codex_default_model() if which == "gpt" else "")
            if selected:
                prompt += MODEL_NOTE.format(model=selected, source="selected in the app" if model_label(name, model) else "from the CLI default config")
            if web:
                prompt += debate.WEB_ON_NOTE
            elif discussion:
                prompt += debate.WEB_OFF_NOTE
            return prompt

        def ask(which: str, prompt: str, round_no: int | None = None, call_mode: str | None = None) -> tuple[str, dict]:
            """모델 1회 호출 + 기록. 성공하면 (답변, 저장된 항목). 실패하면 CliFailure."""
            label, name, model = models[which]
            started = time.time()
            run_info: dict = {}
            call_mode = call_mode or mode
            answer = call_model(which, model, prompt, call_mode, workdir, timeout=timeout, info=run_info, cancel=token,
                                images=images, image_dir=image_dir, web=web,
                                mcp_allow=mcp_allow if which == "claude" else None, cmd_allow=cmd_allow,
                                codex_mcp=mcp_gpt and which == "gpt")
            real = actual_model(which, run_info)
            cli_state.record(which, model, real)
            if run_info.get("web_fallback"):
                self.emit("warning", text=f"{label} CLI가 웹 검색을 지원하지 않아 검색 없이 답했습니다. "
                                          "왼쪽 아래에서 CLI를 업데이트하세요.")
            selected = model_label(name, model) or (codex_default_model() if which == "gpt" else "")
            item = store.append_message(
                conversation_id, "assistant", answer, label,
                cli_model=real or model_label(name, model) or (f"기본값 {selected}" if selected else ""),
                elapsed=round(time.time() - started, 1), mode=call_mode, round=round_no,
                web=(web and not run_info.get("web_fallback")) or None,
                mcp=(mcp if which == "claude" else mcp_gpt) or None,
                # 허용되지 않아 막힌 MCP 호출 → 화면에서 허용 여부를 묻는다
                mcp_denials=[{"tool": d["tool"], "input": json.dumps(d["input"], ensure_ascii=False)[:600]}
                             for d in run_info.get("permission_denials", []) if d["tool"].startswith("mcp__")][:10] or None,
                # 허용 목록에 없어 막힌 명령 → 화면에서 허용 여부를 묻는다
                cmd_denials=[{"command": str(d["input"].get("command", ""))[:500],
                              "prefixes": council_commands.prefixes_for(str(d["input"].get("command", "")))}
                             for d in run_info.get("permission_denials", []) if d["tool"] == "Bash"][:10] or None,
            )
            return answer, item

        def run_parallel(jobs: dict[str, str], round_no: int, on_done) -> dict[str, str]:
            """두 모델을 동시에 호출한다. jobs: which → prompt. 반환: which → 답변 (성공한 것만)."""
            results: dict[str, str] = {}

            def work(which: str, prompt: str) -> None:
                label = models[which][0]
                try:
                    answer, item = ask(which, prompt, round_no, "read" if mode == "work" else None)
                except Cancelled:
                    return
                except CliFailure as exc:
                    key = label if round_no == 1 else f"{label} 교차 검토"
                    errors[key] = exc.details()
                    self.emit("model_error", model=key, text=errors[key])
                    return
                except Exception as exc:  # 예상 못 한 오류도 다른 모델 진행은 막지 않음
                    key = label if round_no == 1 else f"{label} 교차 검토"
                    errors[key] = f"{type(exc).__name__}: {exc}"
                    self.emit("model_error", model=key, text=errors[key])
                    return
                results[which] = answer
                on_done(which, answer, item)
                self.emit("answer", item=item)

            threads = [threading.Thread(target=work, args=(w, p), daemon=True) for w, p in jobs.items()]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            return results

        if not discussion:
            which = target
            label = models[which][0]
            self.emit("stage", step=1, text=f"{label}가 답변하는 중" + (" (웹 검색 사용)" if web else ""))
            try:
                answer, item = ask(which, base_prompt(which))
                answers[label] = answer
                self.emit("answer", item=item)
            except Cancelled:
                stopped = True
            except CliFailure as exc:
                errors[label] = exc.details()
                self.emit("model_error", model=label, text=errors[label])
        else:
            try:
                folder = debate.turn_dir(store, conversation_id)
            except OSError:
                folder = None
            debate.write_log(folder, "질문.md", "질문", question + (f"\n\n(첨부: {', '.join(a['name'] for a in attached)})" if attached else "")
                             + ("\n\n- 웹 검색: 사용" if web else "") + (f"\n- 작업 폴더: {workdir}" if workdir else ""))
            # 1라운드: 서로의 답을 보지 않고 동시에
            self.emit("stage", step=1, text="1라운드 · GPT와 Claude가 각자 독립적으로 답변하는 중" + (" (웹 검색 사용)" if web else ""))
            first = run_parallel({w: base_prompt(w, "plan") + debate.ROUND1_NOTE for w in ("gpt", "claude")}, 1,
                                 lambda w, a, it: debate.write_log(folder, f"1_{models[w][0]}.md", f"{models[w][0]} · 1차 의견", a, it.get("cli_model", "")))
            for w, a in first.items():
                answers[models[w][0]] = a
            stopped = token.cancelled
            second: dict[str, str] = {}
            if len(first) == 2 and not token.cancelled:
                # 2라운드: 상대의 1라운드 답을 읽고 교차 검토
                self.emit("stage", step=2, text="2라운드 · 서로의 답변을 읽고 교차 검토하는 중")
                jobs = {}
                for w, other in (("gpt", "claude"), ("claude", "gpt")):
                    jobs[w] = base_prompt(w, "plan") + debate.ROUND2_NOTE.format(
                        other=models[other][0], mine=first[w], theirs=first[other])
                second = run_parallel(jobs, 2,
                                      lambda w, a, it: debate.write_log(folder, f"2_{models[w][0]}_검토.md", f"{models[w][0]} · 교차 검토", a, it.get("cli_model", "")))
                stopped = token.cancelled
            if len(first) == 2 and not token.cancelled:
                self.emit("stage", step=3, text="토론 내용을 최종 결론으로 정리하는 중")
                try:
                    synth_info: dict = {}
                    synth_prompt, mapping = debate.blind_synth_prompt(
                        random.SystemRandom(), context=context, question=question, gpt1=first["gpt"], claude1=first["claude"],
                        gpt2=second.get("gpt", "(교차 검토 실패 — 없음)"), claude2=second.get("claude", "(교차 검토 실패 — 없음)"),
                        attachments="\n\n".join(f"### {a['name']}\n{a['summary']}" for a in attached if a["summary"])
                        or ("Attached: " + ", ".join(a["name"] for a in attached) if attached else "(none)"))
                    final = debate.unblind(call_model("claude", claude_model, synth_prompt, "chat", timeout=timeout,
                                                      cancel=token, info=synth_info), mapping)
                    cli_state.record("claude", claude_model, actual_model("claude", synth_info))
                    item = store.append_message(
                        conversation_id, "assistant", final, "Council",
                        cli_model="중립 정리(이름 가림) · Claude" + (f" · {claude_model}" if model_label("claude", claude_model) else ""),
                        debate_dir=str(folder.relative_to(store.data_dir)) if folder else None,
                    )
                    answers["Council"] = final
                    debate.write_log(folder, "결론.md", "Council 최종 결론", final)
                    self.emit("answer", item=item)
                except Cancelled:
                    stopped = True
                except CliFailure as exc:
                    errors["Council"] = exc.details()
                    self.emit("model_error", model="Council", text=errors["Council"])
            if mode == "work" and "Council" in answers and not token.cancelled:
                # 작업 모드 토론: 결론 → 한 모델이 실행 → 다른 모델이 결과를 검토 → 실행한 모델이 수정
                # (두 모델이 같은 파일·같은 블렌더 씬을 동시에 고치면 충돌하므로 순서대로 주고받는다)
                doer, checker = executor, ("claude" if executor == "gpt" else "gpt")
                d_label, c_label = models[doer][0], models[checker][0]

                def step(which, prompt, round_no, stage, log_name, log_title, call_mode=None):
                    nonlocal stopped
                    self.emit("stage", step=round_no + 1, text=stage)
                    try:
                        text, item = ask(which, prompt, round_no, call_mode)
                        debate.write_log(folder, log_name, log_title, text, item.get("cli_model", ""))
                        self.emit("answer", item=item)
                        return text
                    except Cancelled:
                        stopped = True
                    except CliFailure as exc:
                        key = f"{models[which][0]} {log_title.split(' · ')[-1]}"
                        errors[key] = exc.details()
                        self.emit("model_error", model=key, text=errors[key])
                    return None

                report = step(doer, base_prompt(doer) + IMPLEMENT_NOTE.format(conclusion=answers["Council"], other=c_label), 3,
                              f"결론대로 {d_label}가 작업하는 중", f"3_{d_label}_구현.md", f"{d_label} · 구현")
                review = None
                if report is not None and not token.cancelled:
                    review = step(checker, base_prompt(checker, "review") + REVIEW_NOTE.format(
                                      executor=d_label, conclusion=answers["Council"], report=report), 4,
                                  f"{c_label}가 결과를 검토하는 중", f"4_{c_label}_검토.md", f"{c_label} · 검토", "read")
                if review and not review.lstrip().upper().startswith("LGTM") and not token.cancelled:
                    step(doer, base_prompt(doer) + FIX_NOTE.format(reviewer=c_label, review=review), 5,
                         f"검토 내용을 반영해 {d_label}가 수정하는 중", f"5_{d_label}_수정.md", f"{d_label} · 수정")

        if track_git:
            # 끝나면 바뀐 파일·내용을 기록 → 화면에서 확정(커밋) 또는 되돌리기
            try:
                ch = council_edit.changes(workdir)
                if ch["files"]:
                    names = ", ".join(f["path"] for f in ch["files"][:8]) + (" …" if len(ch["files"]) > 8 else "")
                    rec = store.append_message(conversation_id, "edit", f"변경된 파일 {len(ch['files'])}개: {names}", "변경",
                                               workdir=str(workdir), files=ch["files"], diff=ch["diff"], action="pending")
                    self.emit("answer", item=rec)
            except council_edit.EditError as exc:
                self.emit("warning", text=f"변경 내용을 확인하지 못했습니다: {exc}")

        if stopped or token.cancelled:
            done_part = f" 완료된 답변: {', '.join(answers)}." if answers else ""
            elapsed = int(time.time() - started_at)
            detail = [f"방법: {token.reason}" if token.reason else "",
                      f"중지 시점: {getattr(self, 'last_stage', '') or '-'}", f"경과 {elapsed // 60}분 {elapsed % 60}초"]
            text = "사용자가 답변 생성을 중지했습니다 (" + " · ".join(d for d in detail if d) + ")." + done_part
            if answers:
                store.append_message(conversation_id, "error", text, "오류")
            else:  # 답이 하나도 없으면 질문을 다음 맥락에서 제외
                store.append_message(conversation_id, "error", text, "오류", failed_message_id=user_item["id"])
            self.emit("stopped", text=text)
        elif not answers:
            text = "모든 모델 호출이 실패했습니다.\n\n" + "\n\n".join(errors.values())
            # 질문은 원문에 남기되, 실패 기록을 붙여 다음 질문의 모델 컨텍스트에서는 제외한다.
            store.append_message(conversation_id, "error", text, "오류", failed_message_id=user_item["id"])
            self.emit("error", text=text)
        elif errors:
            # 일부만 실패: 화면을 새로고침해도 실패 사실이 보이도록 기록 (모델 컨텍스트에서는 제외)
            text = "일부 모델 호출이 실패했습니다.\n\n" + "\n\n".join(errors.values())
            store.append_message(conversation_id, "error", text, "오류")
        meta = store.detail(conversation_id)["meta"]
        self.emit("done", meta=meta, errors=errors)


def open_browser() -> None:
    time.sleep(0.8)
    webbrowser.open(f"http://{HOST}:{PORT}")


def stop_old_server() -> str:
    """같은 포트에서 돌고 있는 이전 AI Council 서버를 종료시킨다. 반환: 이전 버전 문자열 또는 ''."""
    import urllib.request

    base = f"http://{HOST}:{PORT}"
    try:
        with urllib.request.urlopen(base + "/api/status", timeout=3) as res:
            status = json.loads(res.read().decode("utf-8"))
    except Exception:
        return ""
    if not isinstance(status, dict) or not status.get("ok"):
        return ""
    old = str(status.get("version", "?"))
    try:
        req = urllib.request.Request(base + "/api/shutdown", data=b"{}", headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3).read()
    except Exception:
        pass
    return old


def running_version() -> str:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://{HOST}:{PORT}/api/status", timeout=3) as res:
            status = json.loads(res.read().decode("utf-8"))
        return str(status.get("version", "")) if isinstance(status, dict) and status.get("ok") else ""
    except Exception:
        return ""


class AlreadyRunning(Exception):
    pass


class CouncilServer(ThreadingHTTPServer):
    """포트를 이 서버 하나만 쓰도록 연다.
    Windows 에서는 기본 설정(SO_REUSEADDR)이면 이미 켜진 서버가 있어도 같은 포트를 또 열 수 있어서,
    업데이트 후 새 서버가 뜨더라도 요청은 계속 예전 서버로 가는 문제가 있었다 (V0.9.5 까지)."""
    allow_reuse_address = os.name != "nt"

    def server_bind(self) -> None:
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def bind_server() -> ThreadingHTTPServer:
    # 먼저 이미 켜진 Council 이 있는지 확인한다 (포트를 열 수 있는지로만 판단하면 Windows 에서 겹쳐 뜰 수 있음)
    running = running_version()
    if running == VERSION and not os.environ.get("AI_COUNCIL_NO_BROWSER"):
        raise AlreadyRunning()  # 같은 버전이 켜져 있으면 새로 띄우지 않고 브라우저만 연다
    if running:
        print(f"이미 실행 중이던 AI Council V{running} 서버를 종료하고 새 버전으로 다시 시작합니다...", flush=True)
        # 예전 버전 문제로 여러 개가 겹쳐 떠 있을 수 있으므로 응답이 없을 때까지 모두 종료
        for _ in range(40):
            if not running_version():
                break
            stop_old_server()
            time.sleep(0.5)
    for attempt in range(20):
        try:
            return CouncilServer((HOST, PORT), Handler)
        except OSError:
            time.sleep(0.5)
    raise SystemExit(
        f"포트 {PORT}을(를) 사용할 수 없습니다. 다른 프로그램이 사용 중이거나 이전 서버가 응답하지 않습니다.\n"
        + ("작업 관리자에서 python.exe / pythonw.exe 를 종료한 뒤 다시 실행하세요." if os.name == "nt"
           else "활성 상태 보기(Activity Monitor)에서 Python 을 종료한 뒤 다시 실행하세요.")
    )


LOG_MAX_BYTES = 1_000_000


def use_log_file() -> Path | None:
    """창 없이(pythonw) 실행되면 출력할 곳이 없으므로 data/logs/server.log 로 보낸다."""
    if sys.stdout is not None and sys.stderr is not None:
        return None
    log_dir = store.data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / "server.log"
    if log.exists() and log.stat().st_size > LOG_MAX_BYTES:
        os.replace(log, log.with_suffix(".log.1"))
    handle = open(log, "a", encoding="utf-8", buffering=1)
    handle.write(f"\n===== {time.strftime('%Y-%m-%d %H:%M:%S')} 시작 =====\n")
    sys.stdout = sys.stderr = handle
    return log


def show_error(message: str) -> None:
    """창 없이 실행 중일 때 시작 오류를 알림 창으로 보여 준다."""
    print(message, flush=True)
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, "AI Council", 0x10)
        except Exception:
            pass


def main() -> None:
    log = use_log_file()
    try:
        run(log)
    except AlreadyRunning:
        print("이미 실행 중 → 브라우저만 엽니다.", flush=True)
        if not os.environ.get("AI_COUNCIL_NO_BROWSER"):
            webbrowser.open(f"http://{HOST}:{PORT}")
    except SystemExit as exc:
        if log is not None and exc.code not in (None, 0):
            show_error(str(exc.code))
        raise
    except Exception as exc:
        if log is None:
            raise
        import traceback
        traceback.print_exc()
        show_error(f"AI Council을 시작하지 못했습니다.\n\n{type(exc).__name__}: {exc}\n\n자세한 내용: {log}")
        raise SystemExit(1)


def run(log: Path | None) -> None:
    if not INDEX.exists():
        raise SystemExit(f"Missing UI file: {INDEX}")
    server = bind_server()
    print(f"AI Council V{VERSION}: http://{HOST}:{PORT}  (종료: 화면의 '앱 종료' 또는 Ctrl+C)")
    if not os.environ.get("AI_COUNCIL_NO_BROWSER"):  # 업데이트 후 재시작 때는 브라우저를 새로 열지 않음
        threading.Thread(target=open_browser, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
