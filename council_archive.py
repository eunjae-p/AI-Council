"""ZIP 첨부: 안전하게 풀어서 파일 목록·텍스트 내용·이미지를 모델에 전달한다 (표준 라이브러리 zipfile).

안전 규칙
- 압축 안의 경로가 풀 폴더 밖을 가리키면(.. · 절대 경로 · 드라이브 문자) 건너뛴다 (zip slip 방지).
- 바로가기(심볼릭 링크)·암호 걸린 파일은 풀지 않는다.
- 파일 개수·풀린 전체 크기·압축률에 상한을 둔다 (zip bomb 방지).
- __MACOSX/, .DS_Store 같은 운영체제 부산물은 풀지 않는다.
- Windows 에서 만든 ZIP 은 한글 파일 이름이 cp949 로 들어 있는 경우가 많아 깨지지 않게 다시 읽는다.

결과
- 풀린 폴더: data/attachments/<대화>/<저장 이름>_files/
- 요약(summary): 파일 목록·종류별 개수 (대화 기록에도 남김)
- content: 텍스트·코드 파일 내용 (README → 짧은 파일 순, 전체 글자 수 상한)
- images: 압축 안 이미지 일부 (모델에 이미지로 전달)
"""
from __future__ import annotations

import os
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_ZIP_BYTES = 500 * 1024 * 1024          # 올릴 수 있는 ZIP 크기
MAX_ENTRIES = 5000                         # 풀 파일 개수
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024   # 풀린 전체 크기
MAX_RATIO = 200                            # 파일 하나의 압축률 상한 (큰 파일만 검사)
MAX_TEXT_FILE_BYTES = 512 * 1024           # 이보다 큰 텍스트 파일은 내용을 넣지 않음 (목록에는 표시)
CONTENT_BUDGET = 80_000                    # 모델에 넣을 텍스트 내용 합계
MAX_IMAGES = 8
LIST_LIMIT = 300                           # 요약에 보일 파일 목록 줄 수
SKIP_PARTS = {"__MACOSX", ".git", "node_modules", "__pycache__", ".venv", "venv", ".idea", ".vs"}
SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
TEXT_EXT = {
    ".json", ".txt", ".md", ".py", ".yaml", ".yml", ".csv", ".tsv", ".toml", ".ini", ".cfg", ".conf",
    ".log", ".js", ".mjs", ".cjs", ".ts", ".jsx", ".tsx", ".vue", ".svelte", ".html", ".htm", ".css", ".scss",
    ".xml", ".ps1", ".bat", ".cmd", ".sh", ".command", ".sql", ".java", ".kt", ".c", ".h", ".cpp", ".hpp",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".lua", ".r", ".m", ".mel", ".nk", ".gizmo", ".osl",
    ".glsl", ".hlsl", ".usda", ".srt", ".vtt", ".rst", ".env.example", ".gitignore", ".dockerfile",
}
TEXT_NAMES = {"dockerfile", "makefile", "readme", "license", "requirements.txt", ".gitignore", ".env.example"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


class ArchiveError(ValueError):
    pass


def is_zip_name(name: str) -> bool:
    return Path(str(name)).suffix.lower() == ".zip"


def _entry_name(info: zipfile.ZipInfo) -> str:
    """UTF-8 표시가 없는 이름은 zipfile 이 cp437 로 읽는다 → 한국어 Windows(cp949)로 다시 해석."""
    name = info.filename
    if info.flag_bits & 0x800:
        return name
    try:
        raw = name.encode("cp437")
    except UnicodeEncodeError:
        return name
    for enc in ("utf-8", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return name


def _safe_rel(name: str) -> PurePosixPath | None:
    name = name.replace("\\", "/")
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        return None
    parts = [p for p in PurePosixPath(name).parts if p not in ("", ".")]
    if not parts or any(p == ".." for p in parts):
        return None
    bad = '<>:"|?*'
    if any(any(ch in bad or ord(ch) < 32 for ch in p) or p.endswith((" ", ".")) for p in parts):
        return None
    return PurePosixPath(*parts)


def _is_text(rel: PurePosixPath) -> bool:
    low = rel.name.lower()
    return low in TEXT_NAMES or any(low.endswith(ext) for ext in TEXT_EXT)


def _read_text(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\x00" in data[:4096]:
        return None
    for enc in ("utf-8-sig", "cp949"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def _fmt(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / 1048576:.1f}MB"
    return f"{max(1, round(n / 1024))}KB" if n else "0KB"


def extract(zip_path: Path, dest: Path) -> dict:
    """ZIP 을 dest 에 푼다. 반환: files(풀린 파일 목록), skipped(건너뛴 이유별 개수), total(풀린 크기)"""
    try:
        zf = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ArchiveError(f"ZIP 파일을 열 수 없습니다 (손상되었거나 ZIP 형식이 아님): {exc}") from exc
    files: list[dict] = []
    skipped: dict[str, int] = {}
    total = 0

    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    with zf:
        infos = zf.infolist()
        if len(infos) > MAX_ENTRIES * 4:
            raise ArchiveError(f"ZIP 안의 항목이 너무 많습니다 ({len(infos):,}개, 최대 {MAX_ENTRIES:,}개).")
        for info in infos:
            if info.is_dir():
                continue
            rel = _safe_rel(_entry_name(info))
            if rel is None:
                skip("unsafe")
                continue
            if any(p in SKIP_PARTS for p in rel.parts[:-1]) or rel.name in SKIP_NAMES or rel.name.startswith("._"):
                skip("system")
                continue
            if stat.S_ISLNK(info.external_attr >> 16):
                skip("link")
                continue
            if info.flag_bits & 0x1:
                skip("encrypted")
                continue
            if len(files) >= MAX_ENTRIES:
                skip("limit")
                continue
            if info.file_size > 10 * 1024 * 1024 and info.compress_size and info.file_size / info.compress_size > MAX_RATIO:
                skip("ratio")
                continue
            if total + info.file_size > MAX_TOTAL_BYTES:
                skip("limit")
                continue
            target = (root / Path(*rel.parts)).resolve()
            if root not in target.parents:
                skip("unsafe")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            written = 0
            try:
                with zf.open(info) as src, target.open("wb") as out:
                    while chunk := src.read(1024 * 1024):
                        written += len(chunk)
                        if written > info.file_size + 1024 or total + written > MAX_TOTAL_BYTES:
                            raise ArchiveError("size")  # 머리말과 실제 크기가 다름 → 중단
                        out.write(chunk)
            except (ArchiveError, zipfile.BadZipFile, OSError, RuntimeError, NotImplementedError, EOFError):
                target.unlink(missing_ok=True)
                skip("error")
                continue
            total += written
            files.append({"rel": rel.as_posix(), "path": str(target), "size": written})
    return {"files": files, "skipped": skipped, "total": total}


SKIP_LABELS = {
    "unsafe": "폴더 밖을 가리키는 경로", "system": "운영체제·개발 도구 부산물(__MACOSX, .git, node_modules 등)",
    "link": "바로가기(링크)", "encrypted": "암호 걸린 파일", "limit": "개수·크기 상한 초과",
    "ratio": "비정상적으로 높은 압축률", "error": "풀기 실패",
}


def analyze(name: str, zip_path: Path, summarize_json=None) -> dict:
    """ZIP 을 풀고 모델에 줄 요약·내용·이미지를 만든다. 반환: summary, content, images, folder, count"""
    dest = zip_path.with_name(zip_path.name + "_files")
    result = extract(zip_path, dest)
    files = result["files"]
    if not files:
        raise ArchiveError("ZIP 안에 풀 수 있는 파일이 없습니다." + (
            " (건너뜀: " + ", ".join(f"{SKIP_LABELS[k]} {v}개" for k, v in result["skipped"].items()) + ")" if result["skipped"] else ""))
    kinds: dict[str, int] = {}
    for f in files:
        ext = Path(f["rel"]).suffix.lower() or "(확장자 없음)"
        kinds[ext] = kinds.get(ext, 0) + 1
    folders = {str(PurePosixPath(f["rel"]).parent) for f in files} - {"."}
    lines = [
        f"# ZIP: {name}",
        f"- 파일 {len(files):,}개 · 폴더 {len(folders):,}개 · 풀린 크기 {_fmt(result['total'])}",
        f"- 풀린 위치: {dest}",
        "- 종류: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])[:15]),
    ]
    if result["skipped"]:
        lines.append("- 건너뜀: " + ", ".join(f"{SKIP_LABELS[k]} {v}개" for k, v in result["skipped"].items()))
    lines.append("")
    lines.append("## 파일 목록")
    ordered = sorted(files, key=lambda f: f["rel"].lower())
    lines += [f"- {f['rel']} ({_fmt(f['size'])})" for f in ordered[:LIST_LIMIT]]
    if len(ordered) > LIST_LIMIT:
        lines.append(f"- … 외 {len(ordered) - LIST_LIMIT:,}개")

    # 텍스트 내용: README 먼저, 그다음 얕은 경로·작은 파일 순
    def rank(f):
        rel = PurePosixPath(f["rel"])
        return (0 if rel.name.lower().startswith("readme") else 1, len(rel.parts), f["size"])
    texts = sorted((f for f in files if _is_text(PurePosixPath(f["rel"]))), key=rank)
    parts, budget, included, workflows = [], CONTENT_BUDGET, 0, []
    for f in texts:
        if budget <= 0:
            break
        if f["size"] > MAX_TEXT_FILE_BYTES:
            continue
        try:
            text = _read_text(Path(f["path"]))
        except OSError:
            text = None
        if text is None:
            continue
        if summarize_json and f["rel"].lower().endswith(".json"):
            wf = summarize_json(text, PurePosixPath(f["rel"]).name)
            if wf:
                workflows.append(f"### {f['rel']}\n{wf}")
        cut = text[:budget]
        parts.append(f"===== {f['rel']} =====\n{cut}" + ("\n… (잘림)" if len(cut) < len(text) else ""))
        budget -= len(cut)
        included += 1
    if workflows:
        lines += ["", "## ComfyUI 워크플로우 요약"] + workflows
    lines.append("")
    lines.append(f"(텍스트·코드 파일 {len(texts):,}개 중 {included:,}개의 내용을 모델에 전달)")
    images = [f["path"] for f in sorted(files, key=lambda f: f["rel"].lower())
              if Path(f["rel"]).suffix.lower() in IMAGE_EXT and 0 < f["size"] <= 20 * 1024 * 1024][:MAX_IMAGES]
    return {"summary": "\n".join(lines), "content": "\n\n".join(parts), "images": images,
            "folder": str(dest), "count": len(files), "included": included}
