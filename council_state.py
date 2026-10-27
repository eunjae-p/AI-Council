"""모델 표시·사용 횟수 기록 (data/cli_state.json, Git 제외).

- 계정 기본값으로 답했을 때 실제로 쓰인 모델을 기억해 화면에 "기본 (gpt-6.1-sol)"처럼 보여 준다.
  (설정 파일에 기본 모델이 적혀 있으면 그 값을 우선 사용)
- Council 에서 모델을 부른 횟수를 날짜별로 센다. 구독의 남은 사용량은 CLI 가 알려 주지 않으므로
  "오늘 몇 번 썼는지"로 대신 보여 준다.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from council_core import ACCOUNT_DEFAULT, claude_default_model, codex_default_model

KEEP_DAYS = 31
_lock = threading.Lock()


class CliState:
    def __init__(self, data_dir: Path):
        self.path = Path(data_dir) / "cli_state.json"

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def record(self, which: str, selected: str, actual: str) -> None:
        """모델 호출 1회 기록. which: gpt | claude"""
        today = time.strftime("%Y-%m-%d")
        with _lock:
            data = self._load()
            usage = data.setdefault("usage", {})
            day = usage.setdefault(today, {})
            day[which] = int(day.get(which, 0)) + 1
            for old in sorted(usage)[:-KEEP_DAYS]:
                usage.pop(old, None)
            if actual and (not selected or selected == ACCOUNT_DEFAULT):
                data.setdefault("default_seen", {})[which] = {"model": actual, "time": time.time()}
            try:
                self._save(data)
            except OSError:
                pass  # 기록 실패해도 채팅은 계속

    def defaults(self) -> dict:
        """계정 기본값이 실제로 어떤 모델인지. source: config(설정 파일) | seen(최근 답변) | ''(아직 모름)"""
        seen = self._load().get("default_seen", {})
        result = {}
        for which, config in (("gpt", codex_default_model()), ("claude", claude_default_model())):
            if config:
                result[which] = {"model": config, "source": "config"}
            elif (seen.get(which) or {}).get("model"):
                result[which] = {"model": seen[which]["model"], "source": "seen"}
            else:
                result[which] = {"model": "", "source": ""}
        return result

    def forget_default(self, which: str) -> None:
        """계정을 바꾸면 '기본 모델'이 달라질 수 있으므로 기억한 값을 지운다 (사용 횟수는 유지)."""
        with _lock:
            data = self._load()
            if (data.get("default_seen") or {}).pop(which, None) is not None:
                try:
                    self._save(data)
                except OSError:
                    pass

    def usage(self) -> dict:
        usage = self._load().get("usage", {})
        today = time.strftime("%Y-%m-%d")
        since = time.strftime("%Y-%m-%d", time.localtime(time.time() - 6 * 86400))
        week = [d for d in usage if since <= d <= today]  # 오늘 포함 최근 7일
        return {
            "today": {k: int(usage.get(today, {}).get(k, 0)) for k in ("gpt", "claude")},
            "week": {k: sum(int(usage[d].get(k, 0)) for d in week) for k in ("gpt", "claude")},
        }
