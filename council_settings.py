"""⚙ 환경설정 (이 PC 에만 저장: data/settings.json, Git 제외).

- image_dir: 🎨 대화 중 이미지 저장 폴더. 비우면 기본값 = Council 폴더의 image (예: D:\\AI-Council\\image)
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from council_core import ROOT

_lock = threading.Lock()


def default_image_dir() -> Path:
    return Path(os.environ.get("AI_COUNCIL_IMAGE_DIR") or (ROOT / "image"))


class Settings:
    def __init__(self, data_dir: Path) -> None:
        self.path = Path(data_dir) / "settings.json"

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def image_dir(self) -> Path:
        """저장 폴더 (없으면 만든다)."""
        custom = str(self._load().get("image_dir") or "").strip()
        path = Path(custom) if custom else default_image_dir()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def state(self) -> dict:
        custom = str(self._load().get("image_dir") or "").strip()
        return {"image_dir": custom or str(default_image_dir()), "image_dir_default": str(default_image_dir()),
                "image_dir_custom": bool(custom)}

    def set_image_dir(self, value: str) -> dict:
        text = str(value or "").strip().strip('"').strip()
        with _lock:
            data = self._load()
            if not text:
                data.pop("image_dir", None)  # 기본값으로
            else:
                path = Path(text).expanduser()
                if not path.is_absolute():
                    raise ValueError("이미지 저장 폴더는 전체 경로로 입력하세요 (예: D:\\images).")
                try:
                    path.mkdir(parents=True, exist_ok=True)
                except OSError:
                    raise ValueError(f"이미지 저장 폴더를 만들 수 없습니다: {path}") from None
                if not path.is_dir():
                    raise ValueError(f"이미지 저장 폴더를 만들 수 없습니다: {path}")
                data["image_dir"] = str(path.resolve())
            self._save(data)
        return self.state()
