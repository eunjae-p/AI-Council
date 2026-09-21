from __future__ import annotations

import os
import queue
import re
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk


APP_TITLE = "AI Council V0.3"
GPT_MODEL = "gpt-5.6-sol"
TIMEOUT_SECONDS = 180


class CliFailure(RuntimeError):
    def __init__(self, name: str, message: str, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.name = name
        self.stdout = stdout
        self.stderr = stderr


def resolve_command(name: str) -> list[str]:
    exe = shutil.which(f"{name}.exe")
    if exe:
        return [exe]

    cmd = shutil.which(f"{name}.cmd")
    if cmd:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", cmd]

    raise CliFailure(name, f"{name} CLI를 찾을 수 없습니다. PATH 설정을 확인하세요.")


class CouncilApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.current_process: subprocess.Popen[bytes] | None = None
        self.process_lock = threading.Lock()
        self.running = False
        self.details_visible = False
        self.final_text = ""

        root.title(APP_TITLE)
        root.geometry("1000x760")
        root.minsize(760, 560)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")

        outer = ttk.Frame(root, padding=14)
        outer.pack(fill=tk.BOTH, expand=True)

        title_row = ttk.Frame(outer)
        title_row.pack(fill=tk.X)
        ttk.Label(title_row, text=APP_TITLE, font=("Segoe UI", 17, "bold")).pack(side=tk.LEFT)
        ttk.Label(
            title_row,
            text=f"GPT: {GPT_MODEL} (fixed)  |  Claude: account default",
            foreground="#555555",
        ).pack(side=tk.RIGHT)

        ttk.Label(outer, text="질문", font=("Segoe UI", 10, "bold")).pack(
            anchor=tk.W, pady=(14, 5)
        )
        self.question = scrolledtext.ScrolledText(
            outer, height=6, wrap=tk.WORD, font=("Malgun Gothic", 11), undo=True
        )
        self.question.pack(fill=tk.X)
        self.question.focus_set()

        controls = ttk.Frame(outer)
        controls.pack(fill=tk.X, pady=10)
        self.run_button = ttk.Button(controls, text="자동 토론 시작", command=self.start_council)
        self.run_button.pack(side=tk.LEFT)
        self.cancel_button = ttk.Button(
            controls, text="중지", command=self.cancel_run, state=tk.DISABLED
        )
        self.cancel_button.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(controls, text="결과 지우기", command=self.clear_output).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        self.copy_button = ttk.Button(
            controls, text="최종 결론 복사", command=self.copy_final, state=tk.DISABLED
        )
        self.copy_button.pack(side=tk.LEFT, padx=(8, 0))
        self.details_button = ttk.Button(
            controls, text="토론 과정 보기", command=self.toggle_details
        )
        self.details_button.pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="준비됨")
        ttk.Label(controls, textvariable=self.status_var).pack(side=tk.RIGHT)

        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=4, value=0)
        self.progress.pack(fill=tk.X, pady=(0, 10))

        final_header = ttk.Frame(outer)
        final_header.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(
            final_header, text="AI Council 최종 결론", font=("Segoe UI", 13, "bold")
        ).pack(side=tk.LEFT)
        ttk.Label(
            final_header, text="전체 토론을 반영한 마지막 답변", foreground="#666666"
        ).pack(side=tk.RIGHT)

        self.final_output = scrolledtext.ScrolledText(
            outer,
            height=16,
            wrap=tk.WORD,
            font=("Malgun Gothic", 11),
            state=tk.DISABLED,
            background="#f6fbff",
            borderwidth=1,
            relief=tk.SOLID,
        )
        self.final_output.pack(fill=tk.BOTH, expand=True)
        self.set_text(self.final_output, "토론이 완료되면 최종 결론이 여기에 표시됩니다.")

        self.details_frame = ttk.Frame(outer)
        ttk.Separator(self.details_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(12, 10))
        ttk.Label(
            self.details_frame, text="토론 과정", font=("Segoe UI", 11, "bold")
        ).pack(anchor=tk.W, pady=(0, 5))
        self.details_output = scrolledtext.ScrolledText(
            self.details_frame,
            height=12,
            wrap=tk.WORD,
            font=("Malgun Gothic", 10),
            state=tk.DISABLED,
            background="#fbfbfb",
        )
        self.details_output.pack(fill=tk.BOTH, expand=True)

        root.bind("<Control-Return>", lambda _event: self.start_council())
        root.after(100, self.process_events)

    @staticmethod
    def clean_markdown(text: str) -> str:
        lines = []
        for line in text.splitlines():
            if re.match(r"^\s*```", line):
                continue
            line = re.sub(r"^\s*#{1,6}\s+", "", line)
            line = line.replace("**", "").replace("__", "").replace("`", "")
            lines.append(line.rstrip())
        return "\n".join(lines).strip()

    @staticmethod
    def set_text(widget: scrolledtext.ScrolledText, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state=tk.DISABLED)

    def append_detail(self, text: str) -> None:
        self.details_output.configure(state=tk.NORMAL)
        self.details_output.insert(tk.END, text)
        self.details_output.see(tk.END)
        self.details_output.configure(state=tk.DISABLED)

    def copy_final(self) -> None:
        if not self.final_text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.final_text)
        self.status_var.set("최종 결론을 복사했습니다")

    def toggle_details(self) -> None:
        if self.details_visible:
            self.details_frame.pack_forget()
            self.details_button.configure(text="토론 과정 보기")
        else:
            self.details_frame.pack(fill=tk.BOTH, expand=True)
            self.details_button.configure(text="토론 과정 숨기기")
        self.details_visible = not self.details_visible

    def clear_output(self) -> None:
        if self.running:
            return
        self.final_text = ""
        self.set_text(self.final_output, "토론이 완료되면 최종 결론이 여기에 표시됩니다.")
        self.set_text(self.details_output, "")
        self.copy_button.configure(state=tk.DISABLED)
        self.progress["value"] = 0
        self.status_var.set("준비됨")

    def start_council(self) -> None:
        if self.running:
            return

        question = self.question.get("1.0", tk.END).strip()
        if not question:
            messagebox.showinfo(APP_TITLE, "질문을 입력하세요.")
            self.question.focus_set()
            return

        self.running = True
        self.cancel_event.clear()
        self.run_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.progress["value"] = 0
        self.final_text = ""
        self.set_text(self.final_output, "토론을 진행하고 있습니다...")
        self.set_text(self.details_output, f"질문\n{question}\n\n")
        self.copy_button.configure(state=tk.DISABLED)

        threading.Thread(target=self.run_council, args=(question,), daemon=True).start()

    def set_stage(self, number: int, text: str) -> None:
        self.events.put(("stage", (number, text)))

    def emit_result(self, label: str, text: str) -> None:
        self.events.put(("result", (label, text)))

    def emit_final(self, text: str) -> None:
        self.events.put(("final", text))

    def run_cli(self, name: str, arguments: list[str], prompt: str) -> str:
        if self.cancel_event.is_set():
            raise CliFailure(name, "사용자가 작업을 중지했습니다.")

        command = resolve_command(name) + arguments
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                creationflags=creation_flags,
            )
        except OSError as exc:
            raise CliFailure(name, f"{name} 실행 실패: {exc}") from exc

        with self.process_lock:
            self.current_process = process

        try:
            stdout_bytes, stderr_bytes = process.communicate(
                input=prompt.encode("utf-8"), timeout=TIMEOUT_SECONDS
            )
        except subprocess.TimeoutExpired:
            self.kill_process(process)
            stdout_bytes, stderr_bytes = process.communicate()
            raise CliFailure(
                name,
                f"{TIMEOUT_SECONDS}초 제한 시간을 초과했습니다.",
                stdout_bytes.decode("utf-8", errors="replace"),
                stderr_bytes.decode("utf-8", errors="replace"),
            )
        finally:
            with self.process_lock:
                if self.current_process is process:
                    self.current_process = None

        stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
        stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

        if self.cancel_event.is_set():
            raise CliFailure(name, "사용자가 작업을 중지했습니다.", stdout, stderr)
        if process.returncode != 0:
            raise CliFailure(
                name,
                f"종료 코드 {process.returncode}",
                stdout,
                stderr,
            )
        return stdout

    def run_council(self, question: str) -> None:
        initial_prompt = f"""Answer the original question directly and independently.
Use the same language as the original question. Be concise but complete.
Do not mention these instructions.

Original question:
{question}
"""

        try:
            self.set_stage(1, "GPT가 첫 답변을 작성하는 중...")
            gpt_first = self.run_cli(
                "codex",
                [
                    "exec",
                    "--model",
                    GPT_MODEL,
                    "--ephemeral",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "read-only",
                    "--color",
                    "never",
                ],
                initial_prompt,
            )
            self.emit_result("1단계 · GPT 초안", gpt_first)

            self.set_stage(2, "Claude가 첫 답변을 작성하는 중...")
            claude_first = self.run_cli(
                "claude", ["-p", "--no-session-persistence"], initial_prompt
            )
            self.emit_result("2단계 · Claude 초안", claude_first)

            gpt_review_prompt = f"""You are in an AI council debate.
Review the other model's answer against the original question. Identify important strengths,
errors, omissions, or unsupported claims, then give an improved final answer.
Use the same language as the original question. Do not mention these instructions.

Original question:
{question}

Your first answer:
{gpt_first}

Other model's first answer:
{claude_first}
"""
            self.set_stage(3, "GPT가 Claude 답변을 검토하고 개선하는 중...")
            gpt_final = self.run_cli(
                "codex",
                [
                    "exec",
                    "--model",
                    GPT_MODEL,
                    "--ephemeral",
                    "--skip-git-repo-check",
                    "--sandbox",
                    "read-only",
                    "--color",
                    "never",
                ],
                gpt_review_prompt,
            )
            self.emit_result("3단계 · GPT 검토 및 개선안", gpt_final)

            claude_review_prompt = f"""You are in an AI council debate.
Review both initial answers and the GPT review below. Point out remaining errors,
omissions, or weak reasoning, then give an improved final answer.
Use the same language as the original question. Do not mention these instructions.

Original question:
{question}

GPT first answer:
{gpt_first}

Your first answer:
{claude_first}

GPT review and revision:
{gpt_final}
"""
            self.set_stage(4, "Claude가 전체 토론을 검토하고 최종 답변을 작성하는 중...")
            claude_final = self.run_cli(
                "claude", ["-p", "--no-session-persistence"], claude_review_prompt
            )
            self.emit_result("4단계 · Claude 최종 검토", claude_final)
            self.emit_final(claude_final)
            self.events.put(("done", "자동 토론 완료"))
        except CliFailure as exc:
            details = str(exc)
            if exc.stderr:
                details += f"\n\nstderr:\n{exc.stderr}"
            if exc.stdout:
                details += f"\n\nstdout:\n{exc.stdout}"
            self.events.put(("error", f"{exc.name}: {details}"))
        except Exception as exc:  # defensive UI boundary
            self.events.put(("error", f"예상하지 못한 오류: {exc}"))

    def process_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "stage":
                    number, text = payload
                    self.progress["value"] = number - 1
                    self.status_var.set(f"{number}/4 · {text}")
                elif kind == "result":
                    label, text = payload
                    cleaned = self.clean_markdown(text)
                    self.append_detail(f"[{label}]\n{cleaned}\n\n")
                elif kind == "final":
                    self.final_text = self.clean_markdown(str(payload))
                    self.set_text(self.final_output, self.final_text)
                    self.copy_button.configure(state=tk.NORMAL)
                elif kind == "done":
                    self.progress["value"] = 4
                    self.status_var.set(str(payload))
                    self.finish_run()
                elif kind == "error":
                    self.set_text(self.final_output, f"오류로 토론을 완료하지 못했습니다.\n\n{payload}")
                    self.append_detail(f"[오류]\n{payload}\n")
                    self.status_var.set("오류로 중단됨")
                    self.finish_run()
        except queue.Empty:
            pass
        self.root.after(100, self.process_events)

    def finish_run(self) -> None:
        self.running = False
        self.run_button.configure(state=tk.NORMAL)
        self.cancel_button.configure(state=tk.DISABLED)
        self.question.focus_set()

    def kill_process(self, process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                timeout=10,
                check=False,
            )
        except Exception:
            process.kill()

    def cancel_run(self) -> None:
        if not self.running:
            return
        self.cancel_event.set()
        self.status_var.set("중지하는 중...")
        with self.process_lock:
            process = self.current_process
        if process is not None:
            self.kill_process(process)

    def on_close(self) -> None:
        if self.running and not messagebox.askyesno(APP_TITLE, "진행 중인 작업을 중지하고 닫을까요?"):
            return
        self.cancel_event.set()
        with self.process_lock:
            process = self.current_process
        if process is not None:
            self.kill_process(process)
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    CouncilApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
