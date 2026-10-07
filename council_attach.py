"""채팅 첨부 파일 처리.

- 텍스트 파일: 브라우저가 내용을 보내면 검사 후 data/attachments/<대화 ID>/ 에 원본을 보관한다.
  ComfyUI 워크플로우 JSON이면 council_workflow 로 요약을 만든다.
- 이미지·영상: /api/upload 로 먼저 원본을 올려 두고(save_upload), 채팅 요청에는 저장된 파일 이름만 보낸다.
  영상은 council_media 로 프레임을 뽑아 이미지로 전달한다.
- 모델 프롬프트에는 "요약 + 원본(길면 잘라서)"을, 대화 기록에는 요약만 남겨 다음 질문에서도 참고하게 한다.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import council_media as media
from council_workflow import summarize_text

MAX_FILES = 5
MAX_FILE_CHARS = 2_000_000
RAW_PROMPT_BUDGET = 90_000      # 한 번의 프롬프트에 넣을 원본 최대 글자 수 (전체 첨부 합계)
HISTORY_SUMMARY_CHARS = 4_000   # 대화 기록에 남길 요약 길이
TEXT_EXT = {
    ".json", ".txt", ".md", ".py", ".yaml", ".yml", ".csv", ".tsv", ".toml", ".ini", ".cfg",
    ".log", ".js", ".ts", ".html", ".css", ".xml", ".ps1", ".bat", ".cmd", ".sh",
}
_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(name: str) -> str:
    name = _BAD.sub("_", Path(str(name)).name).strip().rstrip(". ") or "file"
    return name[:120]


def attach_dir(data_dir: Path, conversation_id: str) -> Path:
    return Path(data_dir) / "attachments" / conversation_id


def save_upload(data_dir: Path, conversation_id: str, name: str, stream, length: int) -> dict:
    """이미지·영상 원본을 받아 저장한다. 반환: {id, name, size, kind}"""
    name = safe_name(name).replace(",", "_")  # codex --image 는 쉼표를 구분자로 씀
    kind = media.kind_of(name)
    if not kind:
        raise ValueError(f"{name}: 이미지(png·jpg·webp·gif·bmp) 또는 영상(mp4·mov·mkv·avi·webm 등)만 올릴 수 있습니다.")
    if kind == "video" and not media.ffmpeg_available():
        raise ValueError(media.FFMPEG_MISSING)
    limit = media.MAX_IMAGE_BYTES if kind == "image" else media.MAX_VIDEO_BYTES
    if length <= 0:
        raise ValueError("빈 파일입니다.")
    if length > limit:
        raise ValueError(f"{name}: 파일이 너무 큽니다 (이미지 최대 20MB, 영상 최대 2GB).")
    folder = attach_dir(data_dir, conversation_id)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = folder / f"{stamp}_{name}"
    n = 2
    while target.exists():
        target = folder / f"{stamp}_{n}_{name}"
        n += 1
    remaining = length
    try:
        with target.open("wb") as out:
            while remaining > 0:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise ValueError("업로드가 중간에 끊겼습니다.")
                out.write(chunk)
                remaining -= len(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {"id": target.name, "name": name, "size": length, "kind": kind}


def validate(raw, data_dir: Path | None = None, conversation_id: str = "") -> list[dict]:
    if not raw:
        return []
    if not isinstance(raw, list):
        raise ValueError("첨부 형식이 올바르지 않습니다.")
    if len(raw) > MAX_FILES:
        raise ValueError(f"첨부는 한 번에 {MAX_FILES}개까지 가능합니다.")
    files = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("첨부 형식이 올바르지 않습니다.")
        if item.get("upload"):  # 미리 올린 이미지·영상
            stored = str(item["upload"])
            if data_dir is None or stored != Path(stored).name or stored.startswith("."):
                raise ValueError("첨부 파일 정보가 올바르지 않습니다.")
            path = attach_dir(data_dir, conversation_id) / stored
            if not path.is_file():
                raise ValueError(f"{item.get('name', stored)}: 업로드된 파일을 찾을 수 없습니다. 다시 첨부해 주세요.")
            kind = media.kind_of(stored)
            if not kind:
                raise ValueError(f"{stored}: 지원하지 않는 형식입니다.")
            files.append({"name": safe_name(item.get("name") or stored), "upload": str(path), "kind": kind})
            continue
        name = safe_name(item.get("name", "file"))
        content = item.get("content", "")
        if not isinstance(content, str):
            raise ValueError(f"{name}: 텍스트 파일만 첨부할 수 있습니다.")
        if Path(name).suffix.lower() not in TEXT_EXT:
            raise ValueError(f"{name}: 지원하지 않는 형식입니다. (JSON·텍스트·이미지·영상만 가능)")
        if len(content) > MAX_FILE_CHARS:
            raise ValueError(f"{name}: 파일이 너무 큽니다 (최대 약 2MB).")
        files.append({"name": name, "content": content})
    return files


def process(files: list[dict], data_dir: Path, conversation_id: str) -> list[dict]:
    """원본 저장 + 요약. 반환 항목: name, size, kind, summary, path, images, frames, content(프롬프트용)"""
    out = []
    folder = attach_dir(data_dir, conversation_id)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for f in files:
        if f.get("upload"):
            path = Path(f["upload"])
            item = {"name": f["name"], "size": path.stat().st_size, "kind": f["kind"], "path": str(path),
                    "content": "", "images": [], "frames": [], "summary": "", "error": ""}
            if f["kind"] == "image":
                item["images"] = [str(path)]
                item["summary"] = media.image_summary(f["name"], path)
            else:
                try:
                    meta, frames = media.extract_frames(path, path.with_name(path.name + "_frames"))
                    item["frames"] = frames
                    item["images"] = [fr["path"] for fr in frames]
                    item["summary"] = media.video_summary(f["name"], meta, frames)
                except (media.MediaError, OSError, ValueError) as exc:
                    item["error"] = str(exc)
                    item["summary"] = f"영상 {f['name']}: 분석 준비 실패 — {exc}"
                except Exception as exc:  # ffmpeg 시간 초과 등
                    item["error"] = f"{type(exc).__name__}: {exc}"
                    item["summary"] = f"영상 {f['name']}: 분석 준비 실패 — {item['error']}"
            out.append(item)
            continue
        summary = summarize_text(f["content"], f["name"]) if f["name"].lower().endswith(".json") else ""
        kind = "workflow" if summary else ("json" if f["name"].lower().endswith(".json") else "text")
        path = ""
        try:
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / f"{stamp}_{f['name']}"
            n = 2
            while target.exists():
                target = folder / f"{stamp}_{n}_{f['name']}"
                n += 1
            target.write_text(f["content"], encoding="utf-8")
            path = str(target)
        except OSError:
            pass  # 보관 실패해도 이번 질문 분석은 진행
        out.append({"name": f["name"], "size": len(f["content"]), "kind": kind, "images": [], "frames": [],
                    "summary": summary, "path": path, "content": f["content"], "error": ""})
    return out


def images_for(items: list[dict]) -> list[str]:
    """모델에 이미지로 넘길 파일 경로 (최대 media.MAX_IMAGES_PER_CALL 장)."""
    paths = [p for it in items for p in it.get("images") or [] if Path(p).is_file()]
    return paths[: media.MAX_IMAGES_PER_CALL]


def prompt_block(items: list[dict], resent: bool = False) -> str:
    if not items:
        return ""
    head = ("## Images from an earlier message in this conversation (re-attached so you can see them again)"
            if resent else "## Attached files (the user attached these to the newest question)")
    parts = [head]
    text_items = [it for it in items if it["kind"] not in ("image", "video")]
    budget = RAW_PROMPT_BUDGET
    per_file = max(budget // max(len(text_items), 1), 5_000)
    n_image = 0
    for it in items:
        if it["kind"] == "image":
            n_image += 1
            parts.append(f"### Image #{n_image}: {it['name']}\n{it['summary']}\n(attached as image input; look at it directly)")
            continue
        if it["kind"] == "video":
            first = n_image + 1
            n_image += len(it.get("images") or [])
            parts.append(f"### Video: {it['name']}\n{it['summary']}")
            if it.get("images"):
                parts.append(f"The {len(it['images'])} frames above are attached as image inputs #{first}-#{n_image}, "
                             "in time order. Analyse what is visible across frames (composition, color, artifacts, "
                             "flicker, continuity). Audio is not available.")
            if it.get("error"):
                parts.append(f"(frames could not be extracted: {it['error']})")
            continue
        parts.append(f"### File: {it['name']} ({it['size']:,} chars, {it['kind']})")
        if it["summary"]:
            parts.append("#### Parsed summary (generated by code from the JSON — reliable for node/model/color facts)\n"
                         + it["summary"])
        raw = it["content"]
        limit = min(per_file, budget)
        if len(raw) > limit:
            parts.append(f"#### Raw content (first {limit:,} of {len(raw):,} chars; rely on the parsed summary for the rest)\n"
                         f"```\n{raw[:limit]}\n```")
            budget -= limit
        else:
            parts.append(f"#### Raw content\n```\n{raw}\n```")
            budget -= len(raw)
    return "\n\n".join(parts) + "\n"


def history_records(items: list[dict]) -> list[dict]:
    """대화 기록(JSONL)에 남길 첨부 정보. 원본 내용은 넣지 않는다."""
    records = []
    for it in items:
        rec = {
            "name": it["name"], "size": it["size"], "kind": it["kind"], "path": it["path"],
            "summary": it["summary"][:HISTORY_SUMMARY_CHARS] + ("…" if len(it["summary"]) > HISTORY_SUMMARY_CHARS else ""),
        }
        if it.get("images"):
            rec["images"] = it["images"]
        if it.get("frames"):
            rec["frames"] = it["frames"]
        if it.get("error"):
            rec["error"] = it["error"]
        records.append(rec)
    return records


def recent_media(messages: list[dict], window: int = 10) -> list[dict]:
    """최근 메시지 중 가장 마지막으로 이미지·영상이 첨부된 사용자 메시지의 첨부 기록 (다시 보여주기용)."""
    for item in reversed(messages[-window:]):
        if item.get("role") != "user":
            continue
        media_items = [a for a in item.get("attachments") or [] if a.get("kind") in ("image", "video")
                       and any(Path(p).is_file() for p in a.get("images") or [])]
        if media_items:
            return [{**a, "content": "", "images": [p for p in a.get("images") or [] if Path(p).is_file()]}
                    for a in media_items]
    return []
