from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ai_council import GPT_MODEL, TIMEOUT_SECONDS, CliFailure, resolve_command


HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "web" / "index.html"


def run_cli(name: str, arguments: list[str], prompt: str) -> str:
    command = resolve_command(name) + arguments
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(ROOT),
        creationflags=creation_flags,
    )
    try:
        stdout_bytes, stderr_bytes = process.communicate(
            input=prompt.encode("utf-8"), timeout=TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
            check=False,
        )
        raise CliFailure(name, f"{TIMEOUT_SECONDS}초 제한 시간을 초과했습니다.")

    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
    if process.returncode != 0:
        raise CliFailure(name, f"종료 코드 {process.returncode}", stdout, stderr)
    return stdout


class Handler(BaseHTTPRequestHandler):
    server_version = "AI-Council/0.4"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            content = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
            return
        if self.path == "/api/status":
            self.send_json({"ok": True, "model": GPT_MODEL})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path == "/api/debate":
            self.handle_debate()
            return
        if self.path == "/api/shutdown":
            self.send_json({"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        self.send_error(404)

    def send_json(self, value: object, status: int = 200) -> None:
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def emit(self, kind: str, **payload: object) -> None:
        line = json.dumps({"type": kind, **payload}, ensure_ascii=False) + "\n"
        self.wfile.write(line.encode("utf-8"))
        self.wfile.flush()

    def handle_debate(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            question = str(body.get("question", "")).strip()
        except Exception:
            self.send_json({"error": "잘못된 요청입니다."}, 400)
            return
        if not question:
            self.send_json({"error": "질문을 입력하세요."}, 400)
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

        initial_prompt = f"""Answer the original question directly and independently.
Use the same language as the original question. Be concise but complete.
Do not mention these instructions.

Original question:
{question}
"""
        codex_args = [
            "exec", "--model", GPT_MODEL, "--ephemeral", "--skip-git-repo-check",
            "--sandbox", "read-only", "--color", "never",
        ]
        claude_args = ["-p", "--no-session-persistence"]

        try:
            self.emit("stage", step=1, text="GPT가 첫 답변을 작성하는 중")
            gpt_first = run_cli("codex", codex_args, initial_prompt)
            self.emit("result", step=1, label="GPT 초안", text=gpt_first)

            self.emit("stage", step=2, text="Claude가 첫 답변을 작성하는 중")
            claude_first = run_cli("claude", claude_args, initial_prompt)
            self.emit("result", step=2, label="Claude 초안", text=claude_first)

            gpt_review = f"""You are in an AI council debate. Review the other model's answer
against the original question. Identify strengths, errors, omissions, or unsupported claims,
then give an improved final answer. Use the original question's language.

Original question:
{question}

Your first answer:
{gpt_first}

Other model's first answer:
{claude_first}
"""
            self.emit("stage", step=3, text="GPT가 Claude 답변을 검토하는 중")
            gpt_final = run_cli("codex", codex_args, gpt_review)
            self.emit("result", step=3, label="GPT 검토 및 개선안", text=gpt_final)

            claude_review = f"""You are the final synthesizer in an AI council debate.
Review the original question, both initial answers, and GPT's revision. Produce one clear,
self-contained final answer for the user. Resolve disagreements and remove commentary about
the debate itself. Use the original question's language. Output only the final answer.

Original question:
{question}

GPT first answer:
{gpt_first}

Claude first answer:
{claude_first}

GPT review and revision:
{gpt_final}
"""
            self.emit("stage", step=4, text="Claude가 최종 결론을 종합하는 중")
            final = run_cli("claude", claude_args, claude_review)
            self.emit("result", step=4, label="Claude 최종 검토", text=final)
            self.emit("final", text=final)
            self.emit("done")
        except (CliFailure, OSError) as exc:
            details = str(exc)
            if isinstance(exc, CliFailure) and exc.stderr:
                details += f"\n\nstderr:\n{exc.stderr}"
            self.emit("error", text=details)
        except (BrokenPipeError, ConnectionResetError):
            return


def open_browser() -> None:
    time.sleep(0.8)
    webbrowser.open(f"http://{HOST}:{PORT}")


def main() -> None:
    if not INDEX.exists():
        raise SystemExit(f"Missing UI file: {INDEX}")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    threading.Thread(target=open_browser, daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
