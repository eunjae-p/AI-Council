"""🖥 앱처럼 쓰기: Council 화면을 브라우저 탭 대신 '앱 창'(Edge/Chrome --app)으로 열고, 실행 바로가기를 만든다.

- 앱 창: 주소창·탭 없는 독립 창. Edge → Chrome → Chromium 순으로 찾고, 없으면 기본 브라우저 탭으로 연다.
- 바로가기
  - Windows: 바탕화면 + 시작 메뉴 'AI Council' (pythonw 로 창 없이 서버 실행, Council 아이콘).
    작업 표시줄 고정은 Windows 가 프로그램이 대신 할 수 없게 막아 두어서, 시작 메뉴에서 '작업 표시줄에 고정'.
  - Mac: ~/Applications/AI Council.app (Dock 에 끌어다 놓기).
- 창을 닫아도 서버는 계속 실행된다 (종료는 화면의 '앱 종료').

명령줄: python council_app.py --shortcuts   (설치 도우미가 호출, 만든 경로를 한 줄씩 출력)
"""
from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ICON_ICO = ROOT / "assets" / "council.ico"
ICON_PNG = ROOT / "assets" / "council.png"
APP_NAME = "AI Council"
WINDOW_SIZE = "1400,900"


def find_app_browser() -> str | None:
    """--app 창을 지원하는 브라우저 (Chromium 계열) 실행 파일."""
    if os.name == "nt":
        bases = [os.environ.get(k, "") for k in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
        rels = [r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe",
                r"Chromium\Application\chrome.exe"]
        for rel in rels:
            for base in bases:
                if base and Path(base, rel).is_file():
                    return str(Path(base, rel))
        return shutil.which("msedge") or shutil.which("chrome")
    if sys.platform == "darwin":
        for app in ("Microsoft Edge", "Google Chrome", "Chromium", "Brave Browser"):
            for parent in ("/Applications", str(Path.home() / "Applications")):
                exe = Path(parent, f"{app}.app", "Contents", "MacOS", app)
                if exe.is_file():
                    return str(exe)
        return None
    for name in ("microsoft-edge", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if shutil.which(name):
            return shutil.which(name)
    return None


def open_window(url: str, mode: str = "app") -> str:
    """mode: app(앱 창, 기본) | browser(기본 브라우저 탭). 실제로 연 방식을 돌려준다."""
    if mode != "browser":
        exe = find_app_browser()
        if exe:
            try:
                kw: dict = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
                if os.name == "nt":
                    kw["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                else:
                    kw["start_new_session"] = True
                subprocess.Popen([exe, f"--app={url}", f"--window-size={WINDOW_SIZE}"], **kw)
                return "app"
            except OSError:
                pass
    webbrowser.open(url)
    return "browser"


def _pythonw() -> tuple[str, bool]:
    """(실행 파일, 창 없음 여부). Windows 는 python.exe 옆 pythonw.exe 를 쓴다."""
    exe = Path(sys.executable)
    if os.name == "nt":
        w = exe.with_name("pythonw.exe")
        if w.is_file():
            return str(w), True
        found = shutil.which("pythonw")
        if found and "WindowsApps" not in found:
            return found, True
    return str(exe), False


_PS_SHORTCUTS = r"""
$ErrorActionPreference = 'Stop'
$shell = New-Object -ComObject WScript.Shell
$dirs = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))
foreach ($d in $dirs) {
  if (-not $d) { continue }
  $p = Join-Path $d ($env:AC_NAME + '.lnk')
  $l = $shell.CreateShortcut($p)
  $l.TargetPath = $env:AC_TARGET
  $l.Arguments = $env:AC_ARGS
  $l.WorkingDirectory = $env:AC_ROOT
  $l.IconLocation = $env:AC_ICON + ',0'
  $l.Description = 'AI Council'
  if ($env:AC_MIN -eq '1') { $l.WindowStyle = 7 }
  $l.Save()
  Write-Output $p
}
"""


def install_shortcuts() -> list[str]:
    """실행 바로가기를 만들거나 새로 고친다. 만든 경로 목록. 실패하면 RuntimeError."""
    if os.name == "nt":
        target, windowless = _pythonw()
        env = dict(os.environ, AC_NAME=APP_NAME, AC_TARGET=target,
                   AC_ARGS=f'"{ROOT / "ai_council_web.py"}"', AC_ROOT=str(ROOT),
                   AC_ICON=str(ICON_ICO), AC_MIN="0" if windowless else "1")
        res = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _PS_SHORTCUTS],
                             capture_output=True, text=True, env=env, timeout=60,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        paths = [x.strip() for x in res.stdout.splitlines() if x.strip().lower().endswith(".lnk")]
        if res.returncode != 0 or not paths:
            raise RuntimeError((res.stderr or res.stdout or "PowerShell").strip()[-400:])
        return paths
    if sys.platform == "darwin":
        return [str(_install_mac_app())]
    raise RuntimeError("바로가기 만들기는 Windows·Mac 에서만 지원합니다.")


def _install_mac_app() -> Path:
    app = Path.home() / "Applications" / f"{APP_NAME}.app"
    macos = app / "Contents" / "MacOS"
    res = app / "Contents" / "Resources"
    macos.mkdir(parents=True, exist_ok=True)
    res.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    script = macos / APP_NAME
    script.write_text(
        "#!/bin/bash\n"
        "# AI Council 실행: 서버를 백그라운드로 켜고 앱 창을 연다 (이미 켜져 있으면 창만).\n"
        f'cd "{ROOT}" || exit 1\n'
        'export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH"\n'
        "mkdir -p data/logs\n"
        f'nohup "{py}" ai_council_web.py >> data/logs/server.log 2>&1 &\n',
        encoding="utf-8")
    script.chmod(0o755)
    info = {"CFBundleName": APP_NAME, "CFBundleDisplayName": APP_NAME, "CFBundleExecutable": APP_NAME,
            "CFBundleIdentifier": "io.github.eunjae-p.ai-council", "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": "1.0", "LSUIElement": True}
    icns = res / "council.icns"
    if _make_icns(icns):
        info["CFBundleIconFile"] = "council.icns"
    with open(app / "Contents" / "Info.plist", "wb") as fh:
        plistlib.dump(info, fh)
    subprocess.run(["touch", str(app)], check=False)  # Finder 아이콘 새로 고침
    return app


def _make_icns(dest: Path) -> bool:
    """council.png → .icns (macOS 기본 도구 sips·iconutil). 실패해도 앱은 기본 아이콘으로 동작."""
    if not (shutil.which("sips") and shutil.which("iconutil") and ICON_PNG.is_file()):
        return False
    iconset = dest.with_suffix(".iconset")
    shutil.rmtree(iconset, ignore_errors=True)
    iconset.mkdir()
    try:
        for size in (16, 32, 64, 128, 256, 512):
            for scale in (1, 2):
                px = size * scale
                if px > 512:
                    continue
                name = f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png"
                subprocess.run(["sips", "-z", str(px), str(px), str(ICON_PNG), "--out", str(iconset / name)],
                               capture_output=True, check=True)
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(dest)], capture_output=True, check=True)
        return dest.is_file()
    except (OSError, subprocess.CalledProcessError):
        return False
    finally:
        shutil.rmtree(iconset, ignore_errors=True)


if __name__ == "__main__":
    if "--shortcuts" in sys.argv:
        try:
            for p in install_shortcuts():
                print(p)
        except Exception as exc:  # 설치 도우미가 메시지를 보여 준다
            print(exc, file=sys.stderr)
            sys.exit(1)
