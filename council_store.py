"""AI Council 저장 계층.

파일 구조
    data/conversations/<id>.jsonl      대화 원문 (한 줄 = 메시지 하나, 추가만 함)
    data/conversations/<id>.meta.json  제목·상태·장기 요약 메타데이터
    data/trash/<id>.jsonl, .meta.json  삭제된 대화 (복구 가능)
    data/backups/<id>-<시각>.jsonl     '기록 지우기' 전에 남기는 백업
    exports/*.md                       Markdown 내보내기

원문 JSONL은 절대 다시 쓰지 않는다(기록 지우기 제외, 그때도 백업 후).
검색·목록은 이 클래스 메서드로만 접근하므로 나중에 SQLite FTS로 바꿀 수 있다.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
import uuid
from pathlib import Path

from council_core import ROOT

DATA_DIR = Path(os.environ.get("AI_COUNCIL_DATA_DIR") or (ROOT / "data"))
EXPORT_DIR = Path(os.environ.get("AI_COUNCIL_EXPORT_DIR") or (ROOT / "exports"))

META_VERSION = 1
TITLE_MAX = 60
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_WIN_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WIN_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}

SPEAKER_LABELS = {"user": "사용자", "GPT": "GPT", "Claude": "Claude", "Council": "Council 최종 결론", "오류": "오류 기록"}


def now() -> float:
    return time.time()


def fmt_time(value: float | None) -> str:
    if not value:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(value))


def speaker(item: dict) -> str:
    if item.get("role") == "user":
        return "user"
    return str(item.get("model") or "assistant")


def auto_title(text: str) -> str:
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    first = re.sub(r"\s+", " ", first)
    if len(first) > TITLE_MAX:
        first = first[: TITLE_MAX - 1].rstrip() + "…"
    return first or "새 대화"


def safe_filename(name: str, max_len: int = 80) -> str:
    name = _WIN_BAD.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip().rstrip(". ")
    if not name:
        name = "대화"
    if name.split(".")[0].upper() in _WIN_RESERVED:
        name = "_" + name
    return name[:max_len].rstrip(". ") or "대화"


class ConversationStore:
    def __init__(self, data_dir: Path = DATA_DIR, export_dir: Path = EXPORT_DIR) -> None:
        self.data_dir = Path(data_dir)
        self.conv_dir = self.data_dir / "conversations"
        self.trash_dir = self.data_dir / "trash"
        self.backup_dir = self.data_dir / "backups"
        self.export_dir = Path(export_dir)
        self.lock = threading.RLock()
        self.conv_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 경로 ----------
    @staticmethod
    def check_id(conversation_id: str) -> str:
        if not isinstance(conversation_id, str) or not _ID_RE.match(conversation_id):
            raise ValueError("잘못된 대화 ID입니다.")
        return conversation_id

    def _paths(self, conversation_id: str, trash: bool = False) -> tuple[Path, Path]:
        self.check_id(conversation_id)
        base = self.trash_dir if trash else self.conv_dir
        return base / f"{conversation_id}.jsonl", base / f"{conversation_id}.meta.json"

    def exists(self, conversation_id: str) -> bool:
        return self._paths(conversation_id)[0].exists()

    # ---------- 원문 ----------
    def load_messages(self, conversation_id: str, trash: bool = False) -> list[dict]:
        path = self._paths(conversation_id, trash)[0]
        if not path.exists():
            return []
        items: list[dict] = []
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict) and item.get("role") and item.get("content"):
                    items.append(item)
        return items

    def append_message(self, conversation_id: str, role: str, content: str, model: str = "", **extra: object) -> dict:
        with self.lock:
            jsonl, _ = self._paths(conversation_id)
            if not jsonl.exists():
                raise ValueError("대화를 찾을 수 없습니다.")
            item = {"id": uuid.uuid4().hex[:12], "role": role, "content": content, "model": model, "time": now()}
            item.update({k: v for k, v in extra.items() if v not in (None, "")})
            with jsonl.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            meta = self.get_meta(conversation_id)
            meta["updated_at"] = item["time"]
            meta["message_count"] = int(meta.get("message_count", 0)) + 1
            if role == "user" and meta.get("title_source") != "user" and meta.get("title") in ("", "새 대화", None):
                meta["title"] = auto_title(content)
                meta["title_source"] = "auto"
            self._write_meta(conversation_id, meta)
            return item

    # ---------- 메타 ----------
    def _default_meta(self, conversation_id: str, trash: bool = False) -> dict:
        jsonl, _ = self._paths(conversation_id, trash)
        items = self.load_messages(conversation_id, trash)
        mtime = jsonl.stat().st_mtime if jsonl.exists() else now()
        first_user = next((i for i in items if i.get("role") == "user"), None)
        times = [float(i["time"]) for i in items if isinstance(i.get("time"), (int, float))]
        return {
            "version": META_VERSION,
            "id": conversation_id,
            "title": auto_title(str(first_user["content"])) if first_user else "새 대화",
            "title_source": "auto",
            "created_at": min(times) if times else mtime,
            "updated_at": max(times) if times else mtime,
            "archived": False,
            "deleted_at": None,
            "message_count": len(items),
            "summary": "",
            "summarized_through": 0,
            "summary_model": "",
            "summary_updated_at": None,
            "summary_error": "",
        }

    def get_meta(self, conversation_id: str, trash: bool = False) -> dict:
        _, meta_path = self._paths(conversation_id, trash)
        meta = None
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                meta = None  # 손상된 메타는 원문에서 다시 만든다 (원문은 건드리지 않음)
        if not isinstance(meta, dict):
            meta = self._default_meta(conversation_id, trash)
            if not trash:
                self._write_meta(conversation_id, meta)
        else:
            defaults = self._default_meta(conversation_id, trash) if any(
                k not in meta for k in ("title", "created_at", "message_count")
            ) else {}
            for key, value in defaults.items():
                meta.setdefault(key, value)
            meta.setdefault("summary", "")
            meta.setdefault("summarized_through", 0)
            meta.setdefault("summary_model", "")
            meta.setdefault("summary_error", "")
            meta.setdefault("archived", False)
        meta["id"] = conversation_id
        return meta

    def _write_meta(self, conversation_id: str, meta: dict, trash: bool = False) -> None:
        _, meta_path = self._paths(conversation_id, trash)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = meta_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, meta_path)

    def update_meta(self, conversation_id: str, **changes: object) -> dict:
        with self.lock:
            if not self.exists(conversation_id):
                raise ValueError("대화를 찾을 수 없습니다.")
            meta = self.get_meta(conversation_id)
            meta.update(changes)
            self._write_meta(conversation_id, meta)
            return meta

    # ---------- 대화 관리 ----------
    def create(self) -> dict:
        with self.lock:
            conversation_id = str(uuid.uuid4())
            jsonl, _ = self._paths(conversation_id)
            jsonl.touch()
            meta = self._default_meta(conversation_id)
            meta["created_at"] = meta["updated_at"] = now()
            self._write_meta(conversation_id, meta)
            return meta

    def list(self, scope: str = "all") -> list[dict]:
        """scope: all(활성+보관) | active | archived | trash"""
        trash = scope == "trash"
        base = self.trash_dir if trash else self.conv_dir
        if not base.exists():
            return []
        result = []
        for path in base.glob("*.jsonl"):
            if not _ID_RE.match(path.stem):
                continue
            meta = self.get_meta(path.stem, trash)
            if scope == "active" and meta.get("archived"):
                continue
            if scope == "archived" and not meta.get("archived"):
                continue
            result.append(self._public_meta(meta))
        key = "deleted_at" if trash else "updated_at"
        return sorted(result, key=lambda m: float(m.get(key) or 0), reverse=True)

    @staticmethod
    def _public_meta(meta: dict) -> dict:
        return {
            "id": meta["id"],
            "title": meta.get("title") or "새 대화",
            "title_source": meta.get("title_source", "auto"),
            "created_at": meta.get("created_at"),
            "updated_at": meta.get("updated_at"),
            "archived": bool(meta.get("archived")),
            "deleted_at": meta.get("deleted_at"),
            "message_count": meta.get("message_count", 0),
            "summary": meta.get("summary", ""),
            "summarized_through": meta.get("summarized_through", 0),
            "summary_model": meta.get("summary_model", ""),
            "summary_updated_at": meta.get("summary_updated_at"),
            "summary_error": meta.get("summary_error", ""),
        }

    def detail(self, conversation_id: str) -> dict:
        if not self.exists(conversation_id):
            raise ValueError("대화를 찾을 수 없습니다.")
        meta = self.get_meta(conversation_id)
        items = self.load_messages(conversation_id)
        if meta.get("message_count") != len(items):
            meta = self.update_meta(conversation_id, message_count=len(items))
        return {"meta": self._public_meta(meta), "items": items}

    def rename(self, conversation_id: str, title: str) -> dict:
        title = re.sub(r"\s+", " ", str(title)).strip()[:TITLE_MAX]
        if not title:
            raise ValueError("제목을 입력하세요.")
        return self._public_meta(self.update_meta(conversation_id, title=title, title_source="user"))

    def set_archived(self, conversation_id: str, archived: bool) -> dict:
        return self._public_meta(self.update_meta(conversation_id, archived=bool(archived)))

    def delete(self, conversation_id: str) -> None:
        """휴지통으로 이동 (복구 가능)."""
        with self.lock:
            jsonl, meta_path = self._paths(conversation_id)
            if not jsonl.exists():
                raise ValueError("대화를 찾을 수 없습니다.")
            meta = self.get_meta(conversation_id)
            meta["deleted_at"] = now()
            self.trash_dir.mkdir(parents=True, exist_ok=True)
            t_jsonl, t_meta = self._paths(conversation_id, trash=True)
            if t_jsonl.exists():
                raise ValueError("휴지통에 같은 ID의 대화가 이미 있습니다.")
            shutil.move(str(jsonl), str(t_jsonl))
            self._write_meta(conversation_id, meta, trash=True)
            if meta_path.exists():
                meta_path.unlink()

    def restore(self, conversation_id: str) -> dict:
        with self.lock:
            t_jsonl, t_meta = self._paths(conversation_id, trash=True)
            jsonl, _ = self._paths(conversation_id)
            if not t_jsonl.exists():
                raise ValueError("휴지통에서 대화를 찾을 수 없습니다.")
            if jsonl.exists():
                raise ValueError("같은 ID의 대화가 이미 있습니다.")
            meta = self.get_meta(conversation_id, trash=True)
            meta["deleted_at"] = None
            shutil.move(str(t_jsonl), str(jsonl))
            self._write_meta(conversation_id, meta)
            if t_meta.exists():
                t_meta.unlink()
            return self._public_meta(meta)

    def purge(self, conversation_id: str) -> None:
        """휴지통에 있는 대화만 영구 삭제."""
        with self.lock:
            t_jsonl, t_meta = self._paths(conversation_id, trash=True)
            if not t_jsonl.exists():
                raise ValueError("휴지통에 있는 대화만 영구 삭제할 수 있습니다.")
            t_jsonl.unlink()
            if t_meta.exists():
                t_meta.unlink()

    def clear(self, conversation_id: str) -> str:
        """원문을 백업한 뒤 비운다. 백업 경로를 돌려준다."""
        with self.lock:
            jsonl, _ = self._paths(conversation_id)
            if not jsonl.exists():
                raise ValueError("대화를 찾을 수 없습니다.")
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup = self.backup_dir / f"{conversation_id}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
            shutil.copy2(jsonl, backup)
            jsonl.write_text("", encoding="utf-8")
            self.update_meta(
                conversation_id, message_count=0, summary="", summarized_through=0,
                summary_model="", summary_updated_at=None, summary_error="", updated_at=now(),
            )
            return str(backup)

    # ---------- 검색 ----------
    def search(self, query: str, limit: int = 50, include_archived: bool = True) -> list[dict]:
        query = str(query).strip()
        if not query:
            return []
        needle = query.casefold()
        results: list[dict] = []
        for meta in self.list("all"):
            if meta["archived"] and not include_archived:
                continue
            title = meta["title"]
            title_hit = needle in title.casefold()
            hits = 0
            for index, item in enumerate(self.load_messages(meta["id"])):
                if item.get("role") == "error":
                    continue
                content = str(item.get("content", ""))
                pos = content.casefold().find(needle)
                if pos < 0:
                    continue
                start = max(0, pos - 60)
                end = min(len(content), pos + len(query) + 80)
                snippet = ("…" if start else "") + content[start:end].replace("\n", " ") + ("…" if end < len(content) else "")
                results.append({
                    "conversation_id": meta["id"], "title": title, "archived": meta["archived"],
                    "message_index": index, "message_id": item.get("id"), "speaker": speaker(item),
                    "time": item.get("time"), "snippet": snippet, "kind": "message",
                })
                hits += 1
                if hits >= 5 or len(results) >= limit:
                    break
            if title_hit and not hits:
                results.append({
                    "conversation_id": meta["id"], "title": title, "archived": meta["archived"],
                    "message_index": None, "speaker": "", "time": meta["updated_at"],
                    "snippet": "제목 일치", "kind": "title",
                })
            if len(results) >= limit:
                break
        return results[:limit]

    # ---------- 내보내기 ----------
    def to_markdown(self, conversation_id: str) -> str:
        detail = self.detail(conversation_id)
        meta, items = detail["meta"], detail["items"]
        models = sorted({
            f"{i.get('model')}" + (f" ({i['cli_model']})" if i.get("cli_model") else "")
            for i in items if i.get("role") != "user" and i.get("model")
        })
        lines = [
            f"# {meta['title']}",
            "",
            f"- 생성: {fmt_time(meta.get('created_at'))}",
            f"- 수정: {fmt_time(meta.get('updated_at'))}",
            f"- 메시지: {len(items)}개",
            f"- 응답 모델: {', '.join(models) if models else '-'}",
            f"- 상태: {'보관됨' if meta.get('archived') else '활성'}",
            "",
        ]
        if meta.get("summary"):
            lines += [
                "## 장기 요약",
                "",
                f"_{meta.get('summarized_through', 0)}개 메시지 요약 · {meta.get('summary_model') or '-'} · {fmt_time(meta.get('summary_updated_at'))}_",
                "",
                meta["summary"],
                "",
            ]
        lines += ["## 대화", ""]
        for item in items:
            who = speaker(item)
            label = SPEAKER_LABELS.get(who, who)
            extra = f" · {item['cli_model']}" if item.get("cli_model") else ""
            lines += [f"### {label}{extra}", f"_{fmt_time(item.get('time'))}_", "", str(item.get("content", "")).rstrip(), ""]
        return "\n".join(lines).rstrip() + "\n"

    def export_markdown(self, conversation_id: str) -> tuple[Path, str]:
        markdown = self.to_markdown(conversation_id)
        title = self.get_meta(conversation_id).get("title") or "대화"
        base = safe_filename(f"{title}_{time.strftime('%Y%m%d')}")
        with self.lock:
            self.export_dir.mkdir(parents=True, exist_ok=True)
            path = self.export_dir / f"{base}.md"
            n = 2
            while path.exists():
                path = self.export_dir / f"{base}_{n}.md"
                n += 1
            path.write_text(markdown, encoding="utf-8")
        return path, markdown
