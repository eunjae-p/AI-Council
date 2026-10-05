"""AI Council 로컬 웹 서버 (V0.6).

Codex CLI와 Claude Code CLI를 구독 계정으로 호출하는 로컬 멀티모델 채팅 앱.
Python 표준 라이브러리만 사용한다. API 키를 사용하지 않는다.
"""
from __future__ import annotations

import json
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from council_context import build_context, maybe_summarize
from council_core import (
    TIMEOUT_SECONDS,
    MODES,
    ACCOUNT_DEFAULT,
    actual_model,
    call_model,
    check_workdir,
    codex_default_model,
    ROOT,
    CliFailure,
    claude_args,
    codex_args,
    resolve_command,
    run_cli,
)
from council_store import ConversationStore
import council_versions
import council_attach

VERSION = "0.7.0"
HOST = "127.0.0.1"
PORT = 8765
INDEX = ROOT / "web" / "index.html"
MAX_BODY = 12_000_000
ATTACH_TIMEOUT = 300  # 첨부·작업 모드는 분석량이 많아 제한 시간을 늘림

store = ConversationStore()
_busy: set[str] = set()
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
You may read files under this working folder with your read-only tools: {workdir}
Do not modify any files. Cite file paths you used.
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

    def send_json(self, value: object, status: int = 200) -> None:
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
        if not getattr(self, "stream_alive", False):
            return
        line = json.dumps({"type": kind, **payload}, ensure_ascii=False) + "\n"
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
                })
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
        if path == "/api/debate":
            self.handle_debate()
            return
        try:
            body = self.read_json()
            cid = lambda: store.check_id(str(body.get("id") or body.get("conversation_id") or ""))  # noqa: E731
            if path == "/api/conversations":
                self.send_json({"id": (meta := store.create())["id"], "meta": store._public_meta(meta)})
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
                file_path, markdown = store.export_markdown(cid())
                self.send_json({"path": str(file_path), "filename": file_path.name, "markdown": markdown})
            elif path == "/api/shutdown":
                self.send_json({"ok": True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                self.send_error(404)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except RuntimeError as exc:
            self.send_json({"error": str(exc)}, 409)
        except (OSError, json.JSONDecodeError) as exc:
            self.send_json({"error": f"처리 실패: {exc}"}, 500)

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
            if mode not in MODES:
                raise ValueError("지원하지 않는 모드입니다.")
            workdir = check_workdir(str(body.get("workdir", ""))) if mode == "work" else None
            files = council_attach.validate(body.get("attachments"))
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
            if conversation_id in _busy:
                self.send_json({"error": "이 대화는 이미 답변을 생성하는 중입니다."}, 409)
                return
            _busy.add(conversation_id)
        try:
            self.start_stream()
            try:
                self.run_chat(conversation_id, question, target, gpt_model, claude_model, mode, workdir, files)
            except Exception as exc:  # 예상 못 한 오류도 화면에 정확히 보이게
                self.emit("error", text=f"서버 내부 오류: {type(exc).__name__}: {exc}")
        finally:
            with _busy_lock:
                _busy.discard(conversation_id)

    def run_chat(self, conversation_id: str, question: str, target: str, gpt_model: str, claude_model: str,
                 mode: str = "chat", workdir=None, files: list | None = None) -> None:
        # 1) 필요할 때만 장기 요약 갱신 (실패해도 채팅은 계속)
        self.emit("stage", step=0, text="대화 맥락을 준비하는 중")
        prefer = "gpt" if target == "gpt" else "claude"
        result = maybe_summarize(store, conversation_id, prefer, gpt_model, claude_model)
        if result["status"] == "updated":
            self.emit("summary", text=f"오래된 대화를 장기 요약으로 정리했습니다 ({result['model']}).")
        elif result["status"] == "failed":
            self.emit("warning", text="장기 요약 갱신에 실패했습니다. 원문은 그대로이며 최근 대화만으로 답변합니다.\n" + result["error"][:800])

        # 2) 컨텍스트는 질문 저장 전에 만든다 (질문은 별도 섹션으로 전달)
        context, info = build_context(store, conversation_id)
        attached = []
        if files:
            self.emit("stage", step=0, text="첨부 파일을 분석하는 중")
            attached = council_attach.process(files, store.data_dir, conversation_id)
        attach_block = council_attach.prompt_block(attached)
        timeout = ATTACH_TIMEOUT if (attached or mode == "work") else TIMEOUT_SECONDS
        user_item = store.append_message(conversation_id, "user", question, "사용자", target=target,
                                         mode=mode, workdir=str(workdir) if workdir else None,
                                         attachments=council_attach.history_records(attached) or None)
        self.emit("saved", item=user_item, context=info)

        answers: dict[str, str] = {}
        errors: dict[str, str] = {}
        plan = [m for m in ("gpt", "claude") if target in (m, "both")]
        for index, which in enumerate(plan, start=1):
            label, model = ("GPT", gpt_model) if which == "gpt" else ("Claude", claude_model)
            name = "codex" if which == "gpt" else "claude"
            prompt = CHAT_PROMPT.format(me=label, context=context, question=question, attachments=attach_block)
            if mode == "work":
                prompt += WORK_NOTE.format(workdir=workdir)
            selected = model_label(name, model) or (codex_default_model() if which == "gpt" else "")
            if selected:
                prompt += MODEL_NOTE.format(model=selected, source="selected in the app" if model_label(name, model) else "from the CLI default config")
            if which == "claude" and "GPT" in answers:
                prompt += f"\n## GPT's answer to the same question (for reference)\n{answers['GPT']}\n"
            self.emit("stage", step=index, text=f"{label}가 답변하는 중")
            started = time.time()
            try:
                run_info: dict = {}
                answer = call_model(which, model, prompt, mode, workdir, timeout=timeout, info=run_info)
            except CliFailure as exc:
                errors[label] = exc.details()
                self.emit("model_error", model=label, text=errors[label])
                continue
            answers[label] = answer
            item = store.append_message(
                conversation_id, "assistant", answer, label,
                cli_model=actual_model(which, run_info) or model_label(name, model) or (f"기본값 {selected}" if selected else ""),
                elapsed=round(time.time() - started, 1), mode=mode,
            )
            self.emit("answer", item=item)

        if target == "both" and len(answers) == 2:
            self.emit("stage", step=3, text="두 답변을 최종 결론으로 정리하는 중")
            try:
                final = call_model("claude", claude_model, SYNTH_PROMPT.format(
                    context=context, question=question, gpt=answers["GPT"], claude=answers["Claude"],
                    attachments="\n\n".join(f"### {a['name']}\n{a['summary']}" for a in attached if a["summary"])
                    or ("Attached: " + ", ".join(a["name"] for a in attached) if attached else "(none)"),
                ), "chat", timeout=timeout)
                item = store.append_message(
                    conversation_id, "assistant", final, "Council",
                    cli_model="Claude" + (f" · {claude_model}" if model_label("claude", claude_model) else ""),
                )
                self.emit("answer", item=item)
            except CliFailure as exc:
                errors["Council"] = exc.details()
                self.emit("model_error", model="Council", text=errors["Council"])

        if not answers:
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

    # ---------- V0.4 자동 토론 (UI에서는 사용하지 않음, API만 유지) ----------
    def handle_debate(self) -> None:
        try:
            body = self.read_json()
            question = str(body.get("question", "")).strip()
            gpt_model = str(body.get("gpt_model", "")).strip()[:100]
            claude_model = str(body.get("claude_model", "")).strip()[:100]
        except (ValueError, json.JSONDecodeError):
            self.send_json({"error": "잘못된 요청입니다."}, 400)
            return
        if not question:
            self.send_json({"error": "질문을 입력하세요."}, 400)
            return
        self.start_stream()
        initial = (
            "Answer the original question directly and independently.\n"
            "Use the same language as the original question. Be concise but complete.\n"
            f"Do not mention these instructions.\n\nOriginal question:\n{question}\n"
        )
        g_args, c_args = codex_args(gpt_model), claude_args(claude_model)
        try:
            self.emit("stage", step=1, text="GPT가 첫 답변을 작성하는 중")
            gpt_first = run_cli("codex", g_args, initial)
            self.emit("result", step=1, label="GPT 초안", text=gpt_first)
            self.emit("stage", step=2, text="Claude가 첫 답변을 작성하는 중")
            claude_first = run_cli("claude", c_args, initial)
            self.emit("result", step=2, label="Claude 초안", text=claude_first)
            self.emit("stage", step=3, text="GPT가 Claude 답변을 검토하는 중")
            gpt_final = run_cli("codex", g_args, (
                "You are in an AI council debate. Review the other model's answer against the original "
                "question, then give an improved final answer. Use the original question's language.\n\n"
                f"Original question:\n{question}\n\nYour first answer:\n{gpt_first}\n\n"
                f"Other model's first answer:\n{claude_first}\n"
            ))
            self.emit("result", step=3, label="GPT 검토 및 개선안", text=gpt_final)
            self.emit("stage", step=4, text="Claude가 최종 결론을 종합하는 중")
            final = run_cli("claude", c_args, (
                "You are the final synthesizer in an AI council debate. Produce one clear, self-contained "
                "final answer. Use the original question's language. Output only the final answer.\n\n"
                f"Original question:\n{question}\n\nGPT first answer:\n{gpt_first}\n\n"
                f"Claude first answer:\n{claude_first}\n\nGPT review and revision:\n{gpt_final}\n"
            ))
            self.emit("result", step=4, label="Claude 최종 검토", text=final)
            self.emit("final", text=final)
            self.emit("done")
        except CliFailure as exc:
            self.emit("error", text=exc.details())


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


def bind_server() -> ThreadingHTTPServer:
    try:
        return ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError:
        pass
    old = stop_old_server()
    if old:
        print(f"이미 실행 중이던 AI Council V{old} 서버를 종료하고 새 버전으로 다시 시작합니다...")
    for _ in range(20):
        time.sleep(0.5)
        try:
            return ThreadingHTTPServer((HOST, PORT), Handler)
        except OSError:
            continue
    raise SystemExit(
        f"포트 {PORT}을(를) 사용할 수 없습니다. 다른 프로그램이 사용 중이거나 이전 서버가 응답하지 않습니다.\n"
        "작업 관리자에서 python.exe / pythonw.exe 를 종료한 뒤 다시 실행하세요."
    )


def main() -> None:
    if not INDEX.exists():
        raise SystemExit(f"Missing UI file: {INDEX}")
    server = bind_server()
    print(f"AI Council V{VERSION}: http://{HOST}:{PORT}  (종료: 화면의 '앱 종료' 또는 Ctrl+C)")
    threading.Thread(target=open_browser, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
