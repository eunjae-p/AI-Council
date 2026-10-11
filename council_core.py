"""AI Council 공용 코드: CLI 탐색·호출, 공용 상수, 예외.

웹 서버(ai_council_web.py)와 저장 계층이 함께 사용한다.
API 키를 사용하지 않으며, CLI 실패 시 다른 경로로 우회하지 않는다.
"""
from __future__ import annotations

import json
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


def codex_args(model: str = "", web: bool = False) -> list[str]:
    args = ["--search", "exec"] if web else ["exec"]  # --search 는 exec 앞에 오는 전체 옵션
    if model and model != ACCOUNT_DEFAULT:
        args += ["--model", model]
    args += ["--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only", "--color", "never"]
    return args


def claude_args(model: str = "") -> list[str]:
    # JSON 출력: 답변 본문(result)과 실제로 쓴 모델(modelUsage)을 함께 받는다
    args = ["-p", "--no-session-persistence", "--output-format", "json"]
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
    """진행 중인 CLI 프로세스를 중지하기 위한 토큰 (대화 하나당 하나).
    토론 모드에서는 GPT·Claude 가 동시에 돌기 때문에 여러 프로세스를 함께 관리한다."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._processes: set[subprocess.Popen] = set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()
        with self._lock:
            processes = list(self._processes)
        for process in processes:
            _kill_tree(process)

    def attach(self, process: subprocess.Popen) -> None:
        with self._lock:
            self._processes.add(process)
        if self._event.is_set():  # 시작 직전에 중지된 경우
            _kill_tree(process)

    def detach(self, process: subprocess.Popen | None = None) -> None:
        with self._lock:
            if process is None:
                self._processes.clear()
            else:
                self._processes.discard(process)


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
            cancel.detach(process)
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
CHAT_WEB_SYSTEM_PROMPT = (
    "You are a helpful, knowledgeable assistant in a chat app. You may use web search and web fetch to "
    "verify facts. Prefer official documentation and primary sources, cite the URLs you relied on, and "
    "clearly mark anything you could not verify. Do not read or modify local files."
)
WEB_TOOLS = "WebSearch,WebFetch"
CHAT_IMAGE_SYSTEM_PROMPT = (
    "You are a helpful, knowledgeable assistant in a chat app. The user attached images; open each listed "
    "image file with the Read tool and look at it before answering. Do not read any other files. "
    "Answer directly and conversationally."
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
               timeout: int = TIMEOUT_SECONDS, info: dict | None = None, cancel: CancelToken | None = None,
               images: list[str] | None = None, image_dir: Path | None = None, web: bool = False) -> str:
    """which: gpt | claude.  mode: chat(도구 없음, 빈 폴더) | work(작업 폴더 읽기 전용).
    images: 모델에 보여줄 이미지 파일 경로 (GPT: --image, Claude: 파일 읽기 도구).
    web: 웹 검색 허용 (GPT: codex --search, Claude: WebSearch·WebFetch 도구).
    CLI가 웹 검색 옵션을 모르면 웹 검색 없이 다시 시도하고 info["web_fallback"]=True 로 알린다."""
    if web:
        try:
            return _call_model(which, model, prompt, mode, workdir, timeout, info, cancel, images, image_dir, True)
        except Cancelled:
            raise
        except CliFailure as exc:
            if not any(k in f"{exc.stderr}\n{exc.stdout}".lower() for k in _UNKNOWN_FLAG):
                raise
            if info is not None:
                info["web_fallback"] = True
    return _call_model(which, model, prompt, mode, workdir, timeout, info, cancel, images, image_dir, False)


def _call_model(which, model, prompt, mode, workdir, timeout, info, cancel, images, image_dir, web) -> str:
    images = [str(p) for p in images or []]
    cwd = workdir if mode == "work" and workdir else chat_dir()
    if which == "gpt":
        name, base = "codex", codex_args(model, web)
        extra: list[str] = []  # read-only 샌드박스는 기본 인수에 포함
        for path in images:  # 이미지는 재시도 때도 빠지지 않도록 기본 인수에 넣는다
            base += ["--image", path]
    else:
        name, base = "claude", claude_args(model)
        if images:
            prompt += "\n\n## Image files to open with the Read tool (in this order)\n" + "\n".join(
                f"{i}. {p}" for i, p in enumerate(images, start=1))
        web_tools = ["--allowedTools", WEB_TOOLS] if web else []
        if mode == "work":
            extra = ["--tools", "Read,Glob,Grep" + ("," + WEB_TOOLS if web else ""), "--disallowedTools", "mcp__*"] + web_tools
            if images and image_dir:
                extra += ["--add-dir", str(image_dir)]
        elif images:
            # 이미지 폴더 안에서만 읽기 도구 사용
            cwd = image_dir or Path(images[0]).parent
            extra = ["--tools", "Read" + ("," + WEB_TOOLS if web else ""), "--disallowedTools", "mcp__*", *web_tools,
                     "--system-prompt", CHAT_IMAGE_SYSTEM_PROMPT + (" You may also search the web." if web else "")]
        elif web:
            extra = ["--tools", WEB_TOOLS, "--disallowedTools", "mcp__*", *web_tools, "--system-prompt", CHAT_WEB_SYSTEM_PROMPT]
        else:
            extra = ["--disallowedTools", "*", "--system-prompt", CHAT_SYSTEM_PROMPT]
    try:
        try:
            out = run_cli(name, base + extra, prompt, timeout, cwd, info, cancel)
        except Cancelled:
            raise
        except CliFailure as exc:
            # 설치된 CLI 버전이 옵션을 모르면 기본 인수로 한 번만 다시 시도
            if extra and any(k in f"{exc.stderr}\n{exc.stdout}".lower() for k in _UNKNOWN_FLAG):
                out = run_cli(name, base, prompt, timeout, cwd, info, cancel)
            else:
                raise
    except CliFailure as exc:
        if name == "claude" and not isinstance(exc, Cancelled):
            parsed = _claude_json(exc.stdout)
            if parsed:  # JSON 오류 응답이면 사람이 읽을 본문만 남긴다
                exc.stdout = str(parsed.get("result") or exc.stdout)
        raise
    if name == "claude":
        return _claude_result(out, info)
    return out


def _claude_json(text: str) -> dict | None:
    text = (text or "").strip()
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) and "result" in data else None


def _claude_result(stdout: str, info: dict | None) -> str:
    """claude --output-format json 출력에서 답변과 실제 모델을 꺼낸다. JSON 이 아니면 그대로 (구버전 호환)."""
    data = _claude_json(stdout)
    if data is None:
        return stdout
    text = str(data.get("result") or "").strip()
    if data.get("is_error"):
        raise CliFailure("claude", "Claude가 오류를 반환했습니다.", text, "")
    if not text:
        raise CliFailure("claude", "CLI가 빈 응답을 반환했습니다.", stdout, "")
    usage = data.get("modelUsage") or {}
    if isinstance(usage, dict) and usage and info is not None:
        def score(item):
            name, u = item
            out = (u or {}).get("outputTokens", 0) if isinstance(u, dict) else 0
            return ("haiku" not in name.lower(), out)  # 보조로 쓰인 작은 모델보다 본 답변 모델 우선
        info["claude_model"] = max(usage.items(), key=score)[0]
    return text


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
    if which == "claude":
        return str(info.get("claude_model") or "")
    m = re.search(r"^model:\s*(\S+)", info.get("stderr", ""), re.MULTILINE)
    return m.group(1) if m else ""


def claude_default_model() -> str:
    """Claude Code 기본 모델 설정 (~/.claude/settings.json 의 model, 또는 ANTHROPIC_MODEL). 없으면 빈 문자열."""
    if os.environ.get("ANTHROPIC_MODEL"):
        return os.environ["ANTHROPIC_MODEL"]
    home = os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")
    try:
        data = json.loads((Path(home) / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return str(data.get("model") or "") if isinstance(data, dict) else ""
