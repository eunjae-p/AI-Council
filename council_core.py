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
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"
SETUP_NAME = "Setup.cmd" if IS_WINDOWS else "Setup-mac.command"  # 화면 안내에 쓰는 설치 도우미 이름

if not IS_WINDOWS:
    # Finder 에서 실행하면 터미널 설정(PATH)이 안 읽혀 brew·npm·claude 를 못 찾을 수 있어 흔한 위치를 더한다
    _extra = ["/opt/homebrew/bin", "/usr/local/bin", str(Path.home() / ".local" / "bin"),
              str(Path.home() / ".npm-global" / "bin"), str(Path.home() / ".claude" / "local")]
    _path = os.environ.get("PATH", "").split(os.pathsep)
    os.environ["PATH"] = os.pathsep.join(_path + [d for d in _extra if d not in _path and os.path.isdir(d)])

ACCOUNT_DEFAULT = "account default"
# 이전 버전과의 호환용 이름
GPT_MODEL_LABEL = ACCOUNT_DEFAULT

TIMEOUT_SECONDS = 180
SUMMARY_TIMEOUT_SECONDS = 180


LOGIN_HINT = {"claude": "claude auth login", "codex": "codex login"}
_AUTH_WORDS = ("not logged in", "failed to authenticate", "oauth session expired", "session expired", "could not be refreshed",
               "invalid api key", "please run /login", "authentication_error", "login required",
               "please log in", "please login", "token expired", "refresh token")


def is_auth_error(text: str) -> bool:
    """CLI 출력이 로그인 만료·미로그인 오류인지 (Claude: OAuth session expired, Codex: 401 등)."""
    low = (text or "").lower()
    return any(w in low for w in _AUTH_WORDS)


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
        if is_auth_error(blob):
            tips.append(f"{self.name} 로그인이 만료되었거나 필요합니다. Council 왼쪽 아래 '버전 다시 확인' → 빨간 '로그인하기'를 누르거나, "
                        f"터미널에서 '{LOGIN_HINT.get(self.name, self.name + ' login')}' 를 실행한 뒤 다시 보내세요.")
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


def decode_output(data: bytes) -> str:
    """CLI 출력은 UTF-8, Windows 명령 프롬프트(cmd) 오류는 한글 코드페이지(cp949)일 수 있어 둘 다 처리."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        import locale
        for enc in (locale.getpreferredencoding(False), "cp949"):
            try:
                return data.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return data.decode("utf-8", errors="replace")


def win_cmdline(command: list[str]) -> list[str] | str:
    """.cmd 프로그램(npm.cmd, codex.cmd 등)을 cmd.exe /s /c 로 실행할 때 쓸 명령줄.
    cmd 의 /s 는 명령 전체의 첫·마지막 따옴표를 벗기므로, 경로에 공백이 있으면
    ("C:\\Program Files\\nodejs\\npm.cmd") 'C:\\Program' 을 찾을 수 없다는 오류가 난다 (V0.12.1 까지).
    → .cmd 이하 전체를 한 번 더 따옴표로 감싼 문자열로 넘긴다. 그 외에는 목록 그대로."""
    if len(command) >= 5 and [c.lower() for c in command[1:4]] == ["/d", "/s", "/c"]:
        return subprocess.list2cmdline(command[:4]) + ' "' + subprocess.list2cmdline(command[4:]) + '"'
    return command


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


def codex_args(model: str = "", web: bool = False, disable_mcp: list[str] | tuple = (), write: bool = False) -> list[str]:
    args = ["--search"] if web else []  # --search, -c 는 exec 앞에 오는 전체 옵션
    if write:  # 작업 모드: 샌드박스 안에서 인터넷 허용 (npm·pip 설치 등). 쓰기는 여전히 작업 폴더 안만
        args += ["-c", "sandbox_workspace_write.network_access=true"]
    for server in disable_mcp:  # Codex 에 등록된 MCP 서버는 이번 실행에서 끈다 (GPT 쪽 MCP 는 아직 미지원)
        args += ["-c", f"mcp_servers.{server}.enabled=false"]
    args.append("exec")
    if model and model != ACCOUNT_DEFAULT:
        args += ["--model", model]
    # 작업 모드: 작업 폴더 안에서만 쓰기·명령 실행이 되는 샌드박스 (인터넷은 위 설정으로 허용). 그 외에는 읽기 전용
    args += ["--ephemeral", "--skip-git-repo-check", "--sandbox", "workspace-write" if write else "read-only", "--color", "never"]
    return args


def claude_args(model: str = "", stream: bool = False, persist: bool = False) -> list[str]:
    # JSON 출력: 답변 본문(result)과 실제로 쓴 모델(modelUsage)을 함께 받는다
    # stream: 도구를 쓰는 실행은 한 줄씩(stream-json) 받아 진행 상황(어떤 도구·명령을 쓰는지)을 화면에 보여 준다
    # persist: 작업 모드는 세션을 남겨, 승인 후 같은 세션을 이어서(--resume) 실행한다 (처음부터 다시 하지 않게)
    keep = [] if persist else ["--no-session-persistence"]
    args = ["-p", *keep, "--output-format", "stream-json", "--verbose"] if stream else \
        ["-p", *keep, "--output-format", "json"]
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
    else:
        # Mac·Linux: CLI(codex 등)는 자식 프로세스를 띄우므로 같은 프로세스 그룹 전체를 종료
        import signal
        try:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
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
        self.reason = ""  # 중지 방법 (button | esc) — 기록용

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


def _communicate_lines(process: subprocess.Popen[bytes], prompt: str, timeout: int, on_line) -> tuple[bytes, bytes]:
    """communicate() 와 같지만 stdout 을 한 줄씩 읽으며 on_line(줄) 을 부른다 (진행 상황 표시용)."""
    import threading as _th
    out_chunks: list[bytes] = []
    err_chunks: list[bytes] = []

    def read_out() -> None:
        assert process.stdout is not None
        for raw in process.stdout:
            out_chunks.append(raw)
            try:
                on_line(raw.decode("utf-8", "replace"))
            except Exception:
                pass  # 진행 표시 실패가 작업을 멈추면 안 된다

    def read_err() -> None:
        assert process.stderr is not None
        err_chunks.append(process.stderr.read())

    readers = [_th.Thread(target=read_out, daemon=True), _th.Thread(target=read_err, daemon=True)]
    for t in readers:
        t.start()
    try:
        assert process.stdin is not None
        process.stdin.write(prompt.encode("utf-8"))
        process.stdin.close()
    except (BrokenPipeError, OSError):
        pass
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        for t in readers:
            t.join(0.2)
        raise subprocess.TimeoutExpired(process.args, timeout, b"".join(out_chunks), b"".join(err_chunks))
    for t in readers:
        t.join(10)
    return b"".join(out_chunks), b"".join(err_chunks)


def run_cli(name: str, arguments: list[str], prompt: str, timeout: int = TIMEOUT_SECONDS, cwd: Path | str | None = None,
            info: dict | None = None, cancel: CancelToken | None = None) -> str:
    """CLI에 prompt를 stdin으로 전달하고 stdout을 돌려준다. 실패하면 CliFailure."""
    if cancel is not None and cancel.cancelled:
        raise Cancelled(name)
    command = win_cmdline(resolve_command(name) + arguments)
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(cwd or ROOT),
            creationflags=creation_flags,
            start_new_session=os.name != "nt",  # Mac·Linux: 중지할 때 자식 프로세스까지 함께 끄기 위해 그룹 분리
        )
    except OSError as exc:
        raise CliFailure(name, f"{name} 실행 실패: {exc}") from exc

    if cancel is not None:
        cancel.attach(process)
    on_line = (info or {}).get("on_line")
    try:
        if on_line:
            stdout_bytes, stderr_bytes = _communicate_lines(process, prompt, timeout, on_line)
        else:
            stdout_bytes, stderr_bytes = process.communicate(input=prompt.encode("utf-8"), timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _kill_tree(process)
        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=10)
        except Exception:
            stdout_bytes, stderr_bytes = b"", b""
        stdout_bytes = stdout_bytes or (exc.output or b"")
        stderr_bytes = stderr_bytes or (exc.stderr or b"")
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

    stdout = decode_output(stdout_bytes).strip()
    stderr = decode_output(stderr_bytes).strip()
    if info is not None:
        info["stderr"] = stderr
    if process.returncode != 0:
        raise CliFailure(name, f"종료 코드 {process.returncode}", stdout, stderr)
    if not stdout:
        raise CliFailure(name, "CLI가 빈 응답을 반환했습니다.", stdout, stderr)
    return stdout


# ---------- 대화 모드 / 작업 모드 ----------
# chat: 도구 없음 · work: 작업 폴더에서 읽기·만들기·고치기·명령 실행(허용 목록 + 승인)
# read: 작업 폴더 읽기만 (토론 1·2라운드의 계획 단계에서 내부적으로 사용) · edit: 예전 이름 (= work)
# image: 🎨 이미지 생성 (GPT 가 Codex 이미지 생성 도구로 만들고, 작업 폴더 = 저장 폴더)
MODES = {"chat", "work", "edit", "read", "image"}
FOLDER_MODES = {"work", "edit", "read", "image"}
WRITE_MODES = {"work", "edit"}
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
MCP_RULE = (
    "\n\n## Connected tools (MCP)\n"
    "You may use MCP tools connected to the user's account when they help answer the question. Some tools are "
    "pre-approved; if you call one that is not approved, it will be blocked and the user will be asked to approve it, "
    "so do not retry it — just explain what you wanted to look up and why. Never use tools to create, generate, "
    "modify, delete, send, publish, purchase or spend credits/money unless the user's newest message explicitly asks "
    "for that exact action. Say which tool results your answer relies on.\n"
)

# ---------- Codex 에 등록된 MCP 서버 목록 (GPT 실행 때 끄기 위해) ----------
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
_codex_mcp_cache: list = [0.0, []]


_MCP_HEADER = re.compile(r"^\s*\[mcp_servers\.([A-Za-z0-9_-]+)\]\s*(#.*)?$")


def codex_mcp_servers(ttl: float = 300) -> list[str]:
    """~/.codex/config.toml 에 [mcp_servers.이름] 으로 직접 적힌 서버 이름.
    (`codex mcp list` 에는 설정 파일 밖에서 온 서버도 나오는데, 그런 서버에 -c 로 enabled=false 만 넣으면
     내용 없는 서버가 새로 생겨 Codex 가 "invalid transport" 오류로 시작하지 못한다 — V0.11.0 문제)"""
    import time as _time
    if _time.time() - _codex_mcp_cache[0] < ttl:
        return _codex_mcp_cache[1]
    home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    names: list[str] = []
    try:
        for line in (Path(home) / "config.toml").read_text(encoding="utf-8").splitlines():
            m = _MCP_HEADER.match(line)
            if m and m.group(1) not in names:
                names.append(m.group(1))
    except OSError:
        names = []
    _codex_mcp_cache[:] = [_time.time(), names]
    return names


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
               images: list[str] | None = None, image_dir: Path | None = None, web: bool = False,
               mcp_allow: list[str] | None = None, cmd_allow: list[str] | None = None, codex_mcp: bool = False,
               resume: str | None = None) -> str:
    """which: gpt | claude.  mode: chat(도구 없음, 빈 폴더) | work(작업 폴더 읽기 전용).
    images: 모델에 보여줄 이미지 파일 경로 (GPT: --image, Claude: 파일 읽기 도구).
    web: 웹 검색 허용 (GPT: codex --search, Claude: WebSearch·WebFetch 도구).
    CLI가 웹 검색 옵션을 모르면 웹 검색 없이 다시 시도하고 info["web_fallback"]=True 로 알린다.
    mcp_allow: None 이면 MCP 끔. 목록이면 Claude 의 MCP 를 켜고 그 도구들만 승인 없이 실행 허용
               (나머지 MCP 도구는 CLI 가 막고, 막힌 호출은 info["permission_denials"] 로 돌려준다).
    cmd_allow: 작업 모드에서 묻지 않고 실행할 명령 접두어 (council_commands). 나머지 명령은 막히고 승인 요청.
    codex_mcp: GPT(Codex) 에 등록된 MCP 서버(블렌더 등)를 켠다. 끄면 이번 실행에서 모두 끈다.
    resume: Claude 작업 모드에서 승인 후 이어서 실행할 세션 ID (--resume). info["claude_session"] 에 새 세션 ID."""
    if web:
        try:
            return _call_model(which, model, prompt, mode, workdir, timeout, info, cancel, images, image_dir, True, mcp_allow,
                               cmd_allow, codex_mcp, resume)
        except Cancelled:
            raise
        except CliFailure as exc:
            if not any(k in f"{exc.stderr}\n{exc.stdout}".lower() for k in _UNKNOWN_FLAG):
                raise
            if info is not None:
                info["web_fallback"] = True
    return _call_model(which, model, prompt, mode, workdir, timeout, info, cancel, images, image_dir, False, mcp_allow,
                       cmd_allow, codex_mcp, resume)


def _call_model(which, model, prompt, mode, workdir, timeout, info, cancel, images, image_dir, web,
                mcp_allow=None, cmd_allow=None, codex_mcp=False, resume=None) -> str:
    from council_commands import rules as command_rules
    images = [str(p) for p in images or []]
    cwd = workdir if mode in FOLDER_MODES and workdir else chat_dir()
    if which == "gpt":
        disabled = [] if codex_mcp else codex_mcp_servers()
        if codex_mcp:
            prompt += MCP_RULE
        name, base = "codex", codex_args(model, web, disabled, write=mode in WRITE_MODES or mode == "image")
        extra: list[str] = []  # read-only 샌드박스는 기본 인수에 포함
        for path in images:  # 이미지는 재시도 때도 빠지지 않도록 기본 인수에 넣는다
            base += ["--image", path]
    else:
        disabled = []
        persist = mode in WRITE_MODES
        name, base = "claude", claude_args(model, persist=persist)
        if images:
            prompt += "\n\n## Image files to open with the Read tool (in this order)\n" + "\n".join(
                f"{i}. {p}" for i, p in enumerate(images, start=1))
        mcp = mcp_allow is not None
        if mcp:
            prompt += MCP_RULE
        builtin = ["Read", "Glob", "Grep"] if mode in FOLDER_MODES else (["Read"] if images else [])
        if mode in WRITE_MODES:
            # 파일 만들기·고치기 + 명령 실행. 명령은 허용 목록(접두어)만 바로 실행되고 나머지는 막혀 승인 요청으로 돌아온다
            builtin += ["Edit", "Write", "Bash"]
        if web:
            builtin += WEB_TOOLS.split(",")
        if mode not in FOLDER_MODES and images:
            cwd = image_dir or Path(images[0]).parent  # 이미지 폴더 안에서만 읽기 도구 사용
        if not builtin and not mcp:
            # 순수 대화: 도구·MCP 모두 없음
            extra = ["--disallowedTools", "*", "--strict-mcp-config", "--system-prompt", CHAT_SYSTEM_PROMPT]
        else:
            extra = ["--tools", ",".join(builtin)]  # 기본 도구는 읽기·웹 검색만 (빈 문자열이면 없음)
            if mode in FOLDER_MODES and images and image_dir:
                extra += ["--add-dir", str(image_dir)]
            approved = (WEB_TOOLS.split(",") if web else []) + [t for t in (mcp_allow or []) if t.startswith("mcp__")]
            if mode in WRITE_MODES:
                approved += command_rules(cmd_allow or [])
            if approved:
                extra += ["--allowedTools", ",".join(approved)]
            if mode in WRITE_MODES:
                extra += ["--permission-mode", "acceptEdits"]  # 작업 폴더 안 파일 편집만 자동 승인 (명령은 위 허용 목록만)
            if not mcp:
                extra += ["--strict-mcp-config", "--disallowedTools", "mcp__*"]
            if mode not in FOLDER_MODES:
                if images:
                    system = CHAT_IMAGE_SYSTEM_PROMPT + (" You may also search the web." if web else "")
                elif web:
                    system = CHAT_WEB_SYSTEM_PROMPT
                else:
                    system = CHAT_SYSTEM_PROMPT.replace("You have no tools and no file access in this mode.",
                                                        "You have no file access in this mode.")
                if mcp:
                    system += " You may use the MCP tools connected to the user's account, following the rules in the prompt."
                extra += ["--system-prompt", system]
    if name == "claude" and info is not None and info.get("on_progress") and extra[:2] != ["--disallowedTools", "*"]:
        # 도구를 쓰는 실행: 한 줄씩 받아 어떤 도구·명령을 쓰는지 바로 보여 준다
        base = claude_args(model, stream=True, persist=mode in WRITE_MODES)
        info["on_line"] = lambda line, cb=info["on_progress"]: _claude_progress(line, cb)
    if name == "claude" and resume and mode in WRITE_MODES:
        base = base + ["--resume", resume]  # 승인 후: 멈춘 세션에서 이어서 (읽은 파일·실행 결과를 다시 하지 않음)
    try:
        try:
            out = run_cli(name, base + extra, prompt, timeout, cwd, info, cancel)
        except Cancelled:
            raise
        except CliFailure as exc:
            blob = f"{exc.stderr}\n{exc.stdout}"
            if name == "codex" and disabled and "config.toml" in blob:
                # MCP 끄기 설정이 Codex 설정과 맞지 않으면 끄기 없이 한 번 더 시도
                base = codex_args(model, web, write=mode in WRITE_MODES or mode == "image") + [x for path in images for x in ("--image", path)]
                if info is not None:
                    info["codex_mcp_not_disabled"] = True
                out = run_cli(name, base + extra, prompt, timeout, cwd, info, cancel)
            elif extra and any(k in blob.lower() for k in _UNKNOWN_FLAG):
                # 설치된 CLI 버전이 옵션을 모르면 기본 인수로 한 번만 다시 시도
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
    if "\n" in text:  # stream-json: 마지막 result 줄
        for line in reversed(text.splitlines()):
            line = line.strip()
            if line.startswith("{") and '"type"' in line:
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(data, dict) and data.get("type") == "result":
                    return data if "result" in data else None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) and "result" in data else None


def _tool_summary(name: str, data: dict) -> str:
    """도구 호출 한 건을 한 줄로: 'Bash: npm install' · 'Blender · execute_blender_code' · 'Write: app.py'"""
    data = data if isinstance(data, dict) else {}
    if name.startswith("mcp__"):
        _, _, rest = name.partition("__")
        server, _, tool = rest.partition("__")
        detail = data.get("code") or data.get("query") or data.get("prompt") or ""
        first = str(detail).strip().splitlines()[0][:120] if str(detail).strip() else ""
        return f"🔌 {server.replace('claude_ai_', '')} · {tool or rest}" + (f" — {first}" if first else "")
    if name == "Bash":
        return f"$ {str(data.get('command', ''))[:160]}"
    for key in ("file_path", "path", "pattern", "url", "query"):
        if data.get(key):
            return f"{name}: {str(data[key])[:160]}"
    return name


def _claude_progress(line: str, callback) -> None:
    """stream-json 한 줄 → 진행 상황 콜백 (도구 호출, 짧은 설명 글)."""
    line = line.strip()
    if not line.startswith("{"):
        return
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        return
    if not isinstance(msg, dict):
        return
    if msg.get("type") == "system" and msg.get("subtype") == "init":
        servers = [s.get("name", "") + ("" if s.get("status") in (None, "connected") else f"({s.get('status')})")
                   for s in msg.get("mcp_servers") or [] if isinstance(s, dict)]
        callback({"kind": "init", "text": "MCP: " + (", ".join(servers) if servers else "-")})
        return
    if msg.get("type") != "assistant":
        return
    for block in (msg.get("message") or {}).get("content") or []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use":
            callback({"kind": "tool", "text": _tool_summary(str(block.get("name", "")), block.get("input") or {})})
        elif block.get("type") == "text" and str(block.get("text", "")).strip():
            text = " ".join(str(block["text"]).split())
            callback({"kind": "text", "text": text[:200] + ("…" if len(text) > 200 else "")})


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
    denials = data.get("permission_denials") or []
    if info is not None and isinstance(denials, list):
        info["permission_denials"] = [
            {"tool": str(d.get("tool_name", "")), "input": d.get("tool_input") if isinstance(d.get("tool_input"), dict) else {}}
            for d in denials if isinstance(d, dict)
            and (str(d.get("tool_name", "")).startswith("mcp__") or d.get("tool_name") == "Bash")]
    if info is not None and data.get("session_id"):
        info["claude_session"] = str(data["session_id"])
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
