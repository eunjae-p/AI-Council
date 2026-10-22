"""🎨 이미지 모드: GPT(Codex CLI)의 이미지 생성 도구로 이미지를 만들어 원하는 폴더에 저장한다.

흐름
- CLI 는 화면에 이미지를 띄울 수 없으므로, Codex 가 만든 이미지 파일을 Council 이 찾아 저장 폴더로 복사한다.
  · Codex 는 생성한 이미지를 CODEX_HOME(기본 ~/.codex)/generated_images 아래에 남긴다.
  · 모델이 저장 폴더에 직접 저장했으면 그 파일을 쓴다.
- 채팅 화면에서 보이도록 같은 파일을 대화 첨부 폴더(data/attachments/<대화>/generated/)에도 복사한다.
- Claude 에는 이미지 생성 모델이 없다. Claude 를 고르면 Claude 가 프롬프트를 다듬고 생성은 GPT 가 한다.
- 구독(ChatGPT Plus 이상) 사용량으로 생성하며 API 키는 쓰지 않는다.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
SIZES = {"square": "1024x1024", "landscape": "1536x1024", "portrait": "1024x1536"}
MAX_COUNT = 4
SCAN_LIMIT = 5000


def codex_image_dir() -> Path:
    home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    return Path(home) / "generated_images"


def default_output_dir(data_dir: Path) -> Path:
    """저장 폴더를 비워 두면 Council 폴더의 exports/images/<날짜>"""
    export = Path(os.environ.get("AI_COUNCIL_EXPORT_DIR") or (Path(data_dir).parent / "exports"))
    path = export / "images" / time.strftime("%Y-%m-%d")
    path.mkdir(parents=True, exist_ok=True)
    return path


def snapshot(*folders: Path) -> dict[str, float]:
    """폴더 아래 이미지 파일 → 수정 시각 (생성 전후 비교용)."""
    seen: dict[str, float] = {}
    for folder in folders:
        if not folder or not Path(folder).is_dir():
            continue
        count = 0
        for root, _dirs, files in os.walk(folder):
            for name in files:
                if Path(name).suffix.lower() in IMAGE_EXT:
                    p = os.path.join(root, name)
                    try:
                        seen[p] = os.path.getmtime(p)
                    except OSError:
                        pass
                    count += 1
                    if count > SCAN_LIMIT:
                        break
    return seen


def new_images(before: dict[str, float], after: dict[str, float]) -> list[str]:
    return sorted((p for p, m in after.items() if p not in before or m > before[p] + 0.5), key=lambda p: after[p])


def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    n = 2
    while True:
        cand = path.with_name(f"{path.stem}_{n}{path.suffix}")
        if not cand.exists():
            return cand
        n += 1


def collect(created: list[str], output_dir: Path, gallery_dir: Path, prefix: str) -> list[dict]:
    """새로 생긴 이미지를 저장 폴더로 모으고(이미 저장 폴더에 있으면 그대로), 화면 표시용 사본을 만든다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    gallery_dir.mkdir(parents=True, exist_ok=True)
    out_root = output_dir.resolve()
    results = []
    for i, src in enumerate(created, start=1):
        src_path = Path(src)
        try:
            in_output = out_root in src_path.resolve().parents
        except OSError:
            in_output = False
        if in_output:
            saved = src_path
        else:
            saved = _unique(output_dir / f"{prefix}_{i}{src_path.suffix.lower() or '.png'}")
            shutil.copy2(src_path, saved)
        shown = _unique(gallery_dir / saved.name)
        shutil.copy2(saved, shown)
        results.append({"saved": str(saved), "shown": str(shown), "name": saved.name, "size": saved.stat().st_size})
    return results


PROMPT_WRITER_NOTE = """
## Image prompt writing
The user wants an image. You cannot generate images yourself; GPT will generate it with an image model from the
prompt you write. Write the best possible image-generation prompt for the user's request (subject, composition,
style, lighting, colors, mood, text to render if any, what to avoid). If reference images are attached, describe
what to keep from them. Reply with a short note in the user's language, then the final prompt in English inside a
fenced block ```prompt ... ```. Do not ask questions; make reasonable choices.
"""

GENERATE_NOTE = """
## Image generation task
Use your built-in image generation tool to create {count} image(s) for the request below. Do not draw images with
code, SVG, HTML or canvas — use the image generation tool. Size: {size} ({ratio}).
{refs}After generating, save each final image as a PNG file in the current working folder named {prefix}_1.png,
{prefix}_2.png, … (copy it from where the tool saved it if needed). Then reply briefly in the user's language with
what you made and the file names.

### Request
{request}
"""


def extract_prompt(text: str) -> str:
    """Claude 답변에서 ```prompt 블록을 꺼낸다. 없으면 전체."""
    body = text or ""
    for fence in ("```prompt", "```Prompt", "```"):
        i = body.find(fence)
        if i >= 0:
            j = body.find("```", i + len(fence))
            if j > i:
                return body[i + len(fence):j].strip()
    return body.strip()
