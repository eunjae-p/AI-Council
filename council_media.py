"""이미지·영상 첨부 처리.

- 이미지: 그대로 모델에 전달 (GPT: codex --image, Claude: 파일 읽기 도구로 열람)
- 영상: 모델이 영상을 직접 이해하지 못하므로 ffmpeg 로 프레임을 고르게 뽑아 이미지로 전달하고,
  ffprobe 로 얻은 길이·해상도·fps·코덱 정보를 함께 알려준다. (소리는 분석하지 않음)
ffmpeg/ffprobe 가 없으면 영상 분석만 안내 오류를 낸다.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mpg", ".mpeg", ".wmv"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_VIDEO_BYTES = 2 * 1024 * 1024 * 1024
FRAME_COUNT = 12
FRAME_WIDTH = 1280
MAX_IMAGES_PER_CALL = 16
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class MediaError(RuntimeError):
    pass


def kind_of(name: str) -> str:
    ext = Path(name).suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext in VIDEO_EXT:
        return "video"
    return ""


def ffmpeg_available() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _run(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL, creationflags=_NO_WINDOW)


def probe(path: Path) -> dict:
    exe = shutil.which("ffprobe")
    if not exe:
        raise MediaError("영상 분석에는 ffmpeg가 필요합니다. Setup.cmd를 다시 실행해 설치하세요.")
    proc = _run([exe, "-v", "error", "-show_entries",
                 "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt",
                 "-of", "json", str(path)], timeout=60)
    if proc.returncode != 0:
        raise MediaError("영상 정보를 읽지 못했습니다: " + proc.stderr.decode("utf-8", "replace")[-300:])
    data = json.loads(proc.stdout.decode("utf-8", "replace") or "{}")
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
    try:
        duration = float((data.get("format") or {}).get("duration") or 0)
    except ValueError:
        duration = 0.0
    fps_text = video.get("r_frame_rate", "0/1")
    try:
        num, den = fps_text.split("/")
        fps = round(float(num) / float(den), 3) if float(den) else 0.0
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    return {
        "duration": round(duration, 3), "width": video.get("width"), "height": video.get("height"),
        "fps": fps, "codec": video.get("codec_name", ""), "pix_fmt": video.get("pix_fmt", ""),
        "audio": audio.get("codec_name", ""),
    }


def _ts(sec: float) -> str:
    m, s = divmod(max(sec, 0), 60)
    return f"{int(m):02d}:{s:06.3f}"


def extract_frames(path: Path, out_dir: Path, count: int = FRAME_COUNT) -> tuple[dict, list[dict]]:
    """영상 길이 전체에 고르게 프레임을 뽑는다. 반환: (메타, [{path, time}])"""
    exe = shutil.which("ffmpeg")
    if not exe:
        raise MediaError("영상 분석에는 ffmpeg가 필요합니다. Setup.cmd를 다시 실행해 설치하세요.")
    meta = probe(path)
    duration = meta["duration"]
    out_dir.mkdir(parents=True, exist_ok=True)
    if duration <= 0:
        times = [0.0]
    else:
        n = max(1, min(count, int(duration * max(meta["fps"], 1)) or 1))
        times = [duration * (i + 0.5) / n for i in range(n)]  # 구간 중앙 시점
    frames = []
    for i, t in enumerate(times, start=1):
        target = out_dir / f"frame_{i:02d}.jpg"
        proc = _run([exe, "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                     "-vf", f"scale='min({FRAME_WIDTH},iw)':-2", "-q:v", "3", str(target)], timeout=120)
        if proc.returncode == 0 and target.exists() and target.stat().st_size:
            frames.append({"path": str(target), "time": round(t, 3)})
    if not frames:
        raise MediaError("영상에서 프레임을 뽑지 못했습니다. 코덱이 지원되지 않을 수 있습니다.")
    return meta, frames


def video_summary(name: str, meta: dict, frames: list[dict]) -> str:
    lines = [
        f"# 영상 정보: {name}",
        f"- 길이 {_ts(meta['duration'])} ({meta['duration']}초) · 해상도 {meta['width']}×{meta['height']} · "
        f"{meta['fps']} fps · 코덱 {meta['codec']}" + (f" ({meta['pix_fmt']})" if meta.get("pix_fmt") else ""),
        f"- 오디오: {meta['audio'] or '없음'} (소리는 분석 대상이 아님)",
        f"- 분석용 프레임 {len(frames)}장 (길이 전체에서 고르게 추출, 가로 최대 {FRAME_WIDTH}px):",
    ]
    lines += [f"  {i}. {_ts(f['time'])}" for i, f in enumerate(frames, start=1)]
    return "\n".join(lines)


def image_summary(name: str, path: Path) -> str:
    size = path.stat().st_size if path.exists() else 0
    dims = ""
    if shutil.which("ffprobe"):
        try:
            m = probe(path)
            if m.get("width"):
                dims = f" · {m['width']}×{m['height']}"
        except (MediaError, subprocess.TimeoutExpired, ValueError):
            pass
    return f"이미지 {name} ({size / 1024:,.0f}KB{dims})"
