"""🎨 대화 중 이미지: GPT(Codex CLI)의 이미지 생성 도구로 이미지를 만들어 저장 폴더(⚙ 환경설정)에 저장한다.

흐름
- CLI 는 화면에 이미지를 띄울 수 없으므로, Codex 가 만든 이미지 파일을 Council 이 찾아 저장 폴더로 복사한다.
  · Codex 는 생성한 이미지를 CODEX_HOME(기본 ~/.codex)/generated_images 아래에 남긴다.
  · 모델이 저장 폴더에 직접 저장했으면 그 파일을 쓴다.
- 채팅 화면에서 보이도록 같은 파일을 대화 첨부 폴더(data/attachments/<대화>/generated/)에도 복사한다.
- Claude 에는 이미지 생성 모델이 없다. 생성은 GPT 만, Claude 는 만든 이미지를 보고 의견을 줄 수 있다.
- 비율: 기본 16:9, 또는 '생성 전에 묻기'. 장수 1~4.
- 구독(ChatGPT Plus 이상) 사용량으로 생성하며 API 키는 쓰지 않는다.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
RATIOS = ("ask", "16:9", "1:1", "9:16", "4:3", "3:4")
DEFAULT_RATIO = "16:9"
LEGACY_RATIOS = {"square": "1:1", "landscape": "16:9", "portrait": "9:16"}  # 예전 이미지 모드 값
MAX_COUNT = 4
SCAN_LIMIT = 5000


def codex_image_dir() -> Path:
    home = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    return Path(home) / "generated_images"


def norm_ratio(value: object) -> str:
    v = LEGACY_RATIOS.get(str(value or ""), str(value or ""))
    return v if v in RATIOS else DEFAULT_RATIO


def pixel_size(path: Path) -> tuple[int, int] | None:
    """PNG·JPEG·WebP 의 가로×세로 (표준 라이브러리만, 머리 부분만 읽음)."""
    import struct
    try:
        with open(path, "rb") as fh:
            head = fh.read(64 * 1024)
    except OSError:
        return None
    if head[:8] == b"\x89PNG\r\n\x1a\n" and len(head) >= 24:
        return struct.unpack(">II", head[16:24])
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP" and len(head) >= 30:
        kind = head[12:16]
        if kind == b"VP8X":
            return 1 + int.from_bytes(head[24:27], "little"), 1 + int.from_bytes(head[27:30], "little")
        if kind == b"VP8 ":
            w, h = struct.unpack("<HH", head[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if kind == b"VP8L":
            b = int.from_bytes(head[21:25], "little")
            return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    if head[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(head):
            if head[i] != 0xFF:
                i += 1
                continue
            marker = head[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", head[i + 5:i + 9])
                return w, h
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            i += 2 + int.from_bytes(head[i + 2:i + 4], "big")
    return None


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


def _digest(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect(created: list[str], output_dir: Path, gallery_dir: Path, prefix: str, expected: int = 0) -> list[dict]:
    """새로 생긴 이미지를 저장 폴더로 모으고(이미 저장 폴더에 있으면 그대로), 화면 표시용 사본을 만든다.

    GPT 는 이미지 도구 결과(~/.codex/generated_images)를 저장 폴더에 prefix_N.png 로 복사하므로 같은 이미지가 두 곳에 생긴다.
    → 저장 폴더 쪽을 먼저 쓰고, 내용이 같은 이미지는 한 번만. 저장 폴더에 이미 요청 장수(expected)만큼 있으면
      도구 원본 폴더 쪽은 (다시 인코딩돼 내용이 조금 달라도) 쓰지 않는다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    gallery_dir.mkdir(parents=True, exist_ok=True)
    out_root = output_dir.resolve()

    def in_output(p: str) -> bool:
        try:
            return out_root in Path(p).resolve().parents
        except OSError:
            return False

    ordered = [p for p in created if in_output(p)]
    from_tool = [p for p in created if not in_output(p)]
    if expected and len(ordered) >= expected:
        from_tool = []
    results, seen, n = [], set(), 0
    for src in ordered + from_tool:
        src_path = Path(src)
        try:
            digest = _digest(src_path)
        except OSError:
            continue
        if digest in seen:
            continue
        seen.add(digest)
        n += 1
        if in_output(src):
            saved = src_path
        else:
            saved = _unique(output_dir / f"{prefix}_{n}{src_path.suffix.lower() or '.png'}")
            shutil.copy2(src_path, saved)
        shown = _unique(gallery_dir / saved.name)
        shutil.copy2(saved, shown)
        dims = pixel_size(saved)
        results.append({"saved": str(saved), "shown": str(shown), "name": saved.name, "size": saved.stat().st_size,
                        "dims": f"{dims[0]}×{dims[1]}" if dims else ""})
    return results


CHAT_IMAGE_NOTE = """
## Images in this chat
The user turned on image generation for this chat. When the user asks for an image (or a change to an image you made
earlier), create it with your built-in image generation tool — do not draw with code, SVG, HTML or canvas.
{ratio_rule}
Make {count} image(s) per request unless the user asks for a different number.
{refs}After generating, save each final image as a PNG file in the current working folder named {prefix}_1.png,
{prefix}_2.png, … (copy it from where the tool saved it if needed). The user sees the images in the chat automatically,
so do not paste file paths; reply briefly in the user's language about what you made and offer one or two next tweaks.
If the user is only talking (no image requested), answer normally without generating anything.
"""

RATIO_FIXED = ("Aspect ratio for new images: {ratio} — use the image tool's size option for it, or the closest size the tool "
               "supports. If the user asks for another ratio in the message, follow the user. Edits keep the image's ratio "
               "unless the user asks to change it.")

RATIO_ASK = ("Aspect ratio: ask first. Before generating a NEW image, if the user has not said which aspect ratio they want "
             "(in this message or earlier in this chat), do not generate yet: ask in one short question which ratio they want "
             "(e.g. 16:9, 1:1, 9:16, 4:3, 3:4) and stop. Edits of an image you made keep its ratio unless the user asks to change it.")


def ratio_rule(ratio: str) -> str:
    return RATIO_ASK if ratio == "ask" else RATIO_FIXED.format(ratio=ratio)
