"""AI Council 공용 코드: CLI 탐색·호출, 공용 상수, 예외.

웹 서버(ai_council_web.py)와 저장 계층이 함께 사용한다.
API 키를 사용하지 않으며, CLI 실패 시 다른 경로로 우회하지 않는다.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent

ACCOUNT_DEFAULT = "account default"
# 이전 버전과의 호환용 이름
GPT_MODEL_LABEL = ACCOUNT_DEFAULT

TIMEOUT_SECONDS = 180
SUMMARY_TIMEOUT_SECONDS = 180


class CliFailure(RuntimeError):
    def __init__(self, name: str, message: str, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.name = name
        self.stdout = stdout
        self.stderr = stderr

    def hint(self) -> str:
        blob = f"{self.stderr}\n{self.stdout}".lower()
        tips = []
        if "model metadata for" in blob and "not found" in blob:
            tips.append("설치된 Codex CLI가 이 모델을 모릅니다(구버전 가능성). 터미널에서 "
                        "'npm i -g @openai/codex@latest' 로 업데이트한 뒤 AI Council을 다시 시작하세요.")
        if self.name == "claude" and ("or newer is required" in blob or "update claude code" in blob
                                      or "unrecognized_model" in blob):
            tips.append("설치된 Claude Code가 이 모델을 지원하지 않는 구버전입니다. 터미널에서 'claude update' 를 "
                        "실행한 뒤 AI Council을 다시 시작하세요. 그 전까지는 모델을 '계정 기본값'으로 두세요.")
        if "not supported when using codex with a chatgpt account" in blob:
            tips.append("이 GPT 모델은 ChatGPT 구독 계정의 Codex에서 거절되었습니다. '계정 기본값'에서도 같은 오류라면 "
                        "%USERPROFILE%\\.codex\\config.toml 의 model 설정 때문이니, 그 값을 바꾸거나 "
                        "'모델 설정 → 직접 입력'으로 동작하는 모델을 지정하세요.")
        if "not logged in" in blob or ("login" in blob and "please" in blob):
            tips.append(f"{self.name} CLI 로그인이 필요합니다. 터미널에서 {self.name} 로그인 후 다시 시도하세요.")
        if "rate limit" in blob or "usage limit" in blob:
            tips.append("구독 사용량 한도에 도달했을 수 있습니다. 잠시 후 다시 시도하거나 다른 모델을 선택하세요.")
        return "\n→ ".join(tips)

    def details(self) -> str:
        text = f"{self.name}: {self}"
        hint = self.hint()
        if hint:
            text += f"\n→ {hint}"
        if self.stderr:
            text += f"\n\nstderr:\n{trim_log(self.stderr)}"
        if self.stdout:
            text += f"\n\nstdout:\n{self.stdout[-2000:]}"
        return text


def trim_log(text: str, limit: int = 3000) -> str:
    """CLI 로그에서 프롬프트 에코 등은 빼고 오류·경고 줄 위주로 보여준다."""
    keys = ("error", "warning", "fail", "denied", "invalid", "not found", "unauthorized", "limit", "required", "not support")
    lines = [l for l in text.splitlines() if any(k in l.lower() for k in keys)]
    picked = "\n".join(dict.fromkeys(lines)) if lines else text
    return picked[-limit:]


def resolve_command(name: str) -> list[str]:
    exe = shutil.which(f"{name}.exe")
    if exe:
        return [exe]

    cmd = shutil.which(f"{name}.cmd")
    if cmd:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", cmd]

    if os.name != "nt":  # 개발·테스트 환경(리눅스/맥)용
        plain = shutil.which(name)
        if plain:
            return [plain]

    raise CliFailure(name, f"{name} CLI를 찾을 수 없습니다. PATH 설정을 확인하세요.")


def codex_args(model: str = "") -> list[str]:
    args = ["exec"]
    if model and model != ACCOUNT_DEFAULT:
        args += ["--model", model]
    args += ["--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only", "--color", "never"]
    return args


def claude_args(model: str = "") -> list[str]:
    args = ["-p", "--no-session-persistence"]
    if model and model != ACCOUNT_DEFAULT:
        args += ["--model", model]
    return args


def _kill_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
            timeout=15,
        )
    if process.poll() is None:
        process.kill()


class Cancelled(CliFailure):
    """사용자가 중지 버튼을 눌러 CLI 호출이 취소됨."""

    def __init__(self, name: str):
        super().__init__(name, "사용자가 답변 생성을 중지했습니다.")


class CancelToken:
    """진행 중인 CLI 프로세스를 중지하기 위한 토큰 (대화 하나당 하나)."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._process: subprocess.Popen | None = None

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()
        with self._lock:
            process = self._process
        if process is not None:
            _kill_tree(process)

    def attach(self, process: subprocess.Popen) -> None:
        with self._lock:
            self._process = process
        if self._event.is_set():  # 시작 직전에 중지된 경우
            _kill_tree(process)

    def detach(self) -> None:
        with self._lock:
            self._process = None


def run_cli(name: str, arguments: list[str], prompt: str, timeout: int = TIMEOUT_SECONDS, cwd: Path | str | None = None,
            info: dict | None = None, cancel: CancelToken | None = None) -> str:
    """CLI에 prompt를 stdin으로 전달하고 stdout을 돌려준다. 실패하면 CliFailure."""
    if cancel is not None and cancel.cancelled:
        raise Cancelled(name)
    command = resolve_command(name) + arguments
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd or ROOT),
            creationflags=creation_flags,
        )
    except OSError as exc:
        raise CliFailure(name, f"{name} 실행 실패: {exc}") from exc

    if cancel is not None:
        cancel.attach(process)
    try:
        stdout_bytes, stderr_bytes = process.communicate(input=prompt.encode("utf-8"), timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(process)
        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=10)
        except Exception:
            stdout_bytes, stderr_bytes = b"", b""
        raise CliFailure(
            name,
            f"{timeout}초 제한 시간을 초과했습니다.",
            stdout_bytes.decode("utf-8", errors="replace").strip(),
            stderr_bytes.decode("utf-8", errors="replace").strip(),
        )
    except (BrokenPipeError, OSError):
        # 중지로 프로세스가 먼저 종료되면 stdin 쓰기가 실패할 수 있음
        if cancel is not None and cancel.cancelled:
            raise Cancelled(name)
        raise
    finally:
        if cancel is not None:
            cancel.detach()
    if cancel is not None and cancel.cancelled:
        raise Cancelled(name)

    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()
    if info is not None:
        info["stderr"] = stderr
    if process.returncode != 0:
        raise CliFailure(name, f"종료 코드 {process.returncode}", stdout, stderr)
    if not stdout:
        raise CliFailure(name, "CLI가 빈 응답을 반환했습니다.", stdout, stderr)
    return stdout


# ---------- 대화 모드 / 작업 모드 ----------
MODES = {"chat", "work"}
CHAT_SYSTEM_PROMPT = (
    "You are a helpful, knowledgeable assistant in a chat app. Answer the user's question directly "
    "and conversationally. You have no tools and no file access in this mode."
)
_UNKNOWN_FLAG = ("unknown option", "unexpected argument", "unrecognized", "unknown argument", "invalid option")


def chat_dir() -> Path:
    """대화 모드에서 CLI를 실행할 빈 폴더 (프로젝트 파일에 접근하지 않게)."""
    path = Path(tempfile.gettempdir()) / "ai-council-chat"
    path.mkdir(parents=True, exist_ok=True)
    return path


def check_workdir(workdir: str) -> Path:
    if not workdir or not workdir.strip():
        raise ValueError("작업 모드에서는 작업 폴더를 입력하세요.")
    path = Path(workdir.strip().strip('"')).expanduser()
    if not path.is_dir():
        raise ValueError(f"작업 폴더를 찾을 수 없습니다: {path}")
    return path.resolve()


def call_model(which: str, model: str, prompt: str, mode: str = "chat", workdir: Path | None = None,
               timeout: int = TIMEOUT_SECONDS, info: dict | None = None, cancel: CancelToken | None = None) -> str:
    """which: gpt | claude.  mode: chat(도구 없음, 빈 폴더) | work(작업 폴더 읽기 전용)."""
    if which == "gpt":
        name, base = "codex", codex_args(model)
        extra: list[str] = []  # read-only 샌드박스는 기본 인수에 포함
    else:
        name, base = "claude", claude_args(model)
        if mode == "work":
            extra = ["--tools", "Read,Glob,Grep", "--disallowedTools", "mcp__*"]
        else:
            extra = ["--disallowedTools", "*", "--system-prompt", CHAT_SYSTEM_PROMPT]
    cwd = workdir if mode == "work" and workdir else chat_dir()
    try:
        return run_cli(name, base + extra, prompt, timeout, cwd, info, cancel)
    except Cancelled:
        raise
    except CliFailure as exc:
        # 설치된 CLI 버전이 옵션을 모르면 기본 인수로 한 번만 다시 시도
        if extra and any(k in f"{exc.stderr}\n{exc.stdout}".lower() for k in _UNKNOWN_FLAG):
            return run_cli(name, base, prompt, timeout, cwd, info, cancel)
        raise


# ---------- 실제 사용 모델 확인 ----------
def codex_default_model() -> str:
    """Codex 기본 모델 (~/.codex/config.toml 의 최상위 model 값). 없으면 빈 문자열."""
    home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    path = Path(home) / "config.toml"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):  # 최상위 키만
            break
        m = re.match(r'model\s*=\s*["\']([^"\']+)["\']', stripped)
        if m:
            return m.group(1)
    return ""


def actual_model(which: str, info: dict | None) -> str:
    """CLI 로그에서 실제 사용된 모델명 추출 (Codex는 stderr 머리말에 'model: ...'을 찍음)."""
    if not info:
        return ""
    m = re.search(r"^model:\s*(\S+)", info.get("stderr", ""), re.MULTILINE)
    return m.group(1) if m else ""
