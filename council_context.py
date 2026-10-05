"""모델에 넘길 컨텍스트 구성과 장기 대화 자동 요약.

프롬프트 = 누적 장기 요약 + 최근 대화 원문(메시지 단위) + 현재 질문

- 원문은 메시지 단위로 고른다. 메시지 중간을 자르지 않는다.
  (단, 가장 최근 메시지 하나가 예산보다 크면 그 메시지만 앞부분을 생략 표시와 함께 줄인다.)
- 요약되지 않은 원문이 SUMMARY_TRIGGER_CHARS를 넘을 때만 요약을 갱신한다.
- 최근 KEEP_RECENT_CHARS 분량은 요약하지 않고 원문으로 남긴다.
- 요약 실패 시 meta에 오류만 기록하고 원문은 건드리지 않으며 채팅은 계속된다.
"""
from __future__ import annotations

import time

from council_core import SUMMARY_TIMEOUT_SECONDS, CliFailure, call_model
from council_store import ConversationStore, now, speaker

RECENT_BUDGET_CHARS = 24000      # 프롬프트에 넣을 최근 원문 최대치
SUMMARY_TRIGGER_CHARS = 30000    # 요약 안 된 원문이 이보다 길면 요약 갱신
KEEP_RECENT_CHARS = 12000        # 요약 시 원문으로 남길 최근 분량
SUMMARY_MAX_CHARS = 6000         # 요약문 목표 최대 길이
SUMMARY_INPUT_MAX_CHARS = 60000  # 한 번 요약에 넣을 원문 최대치 (넘으면 여러 번 나눠 요약)

PROMPT_LABELS = {"user": "사용자", "GPT": "GPT", "Claude": "Claude", "Council": "Council 최종 결론"}


def mark_skipped(items: list[dict]) -> list[dict]:
    """모든 모델이 실패한 질문과 오류 기록은 모델 컨텍스트에서 뺀다 (원문 파일에는 그대로 남음)."""
    failed = {i.get("failed_message_id") for i in items if i.get("role") == "error"}
    for item in items:
        if item.get("role") == "error" or (item.get("role") == "user" and item.get("id") in failed):
            item["_skip"] = True
    return items


def message_block(item: dict) -> str:
    if item.get("_skip"):
        return ""
    who = speaker(item)
    text = f"[{PROMPT_LABELS.get(who, who)}]\n{item.get('content', '')}"
    for att in item.get("attachments") or []:
        text += f"\n(첨부: {att.get('name')}, {att.get('size', 0):,}자)"
        if att.get("summary"):
            text += f"\n[첨부 요약: {att.get('name')}]\n{att['summary']}"
    return text


def select_recent(items: list[dict], start: int, budget: int) -> tuple[list[str], int]:
    """items[start:] 중 뒤에서부터 메시지 단위로 budget 안에 들어가는 만큼 고른다.
    반환: (블록 목록, 포함된 첫 메시지 인덱스)"""
    blocks: list[str] = []
    used = 0
    first = len(items)
    for index in range(len(items) - 1, start - 1, -1):
        block = message_block(items[index])
        if not block:
            first = index
            continue
        cost = len(block) + 2
        if used + cost > budget:
            if not blocks:  # 가장 최근 메시지 하나가 너무 큰 경우만 앞부분 생략
                keep = max(budget - 200, 1000)
                header, _, body = block.partition("\n")
                blocks.append(f"{header}\n(앞부분 {len(body) - keep:,}자 생략)\n…{body[-keep:]}")
                first = index
            break
        blocks.append(block)
        used += cost
        first = index
    blocks.reverse()
    return blocks, first


def unsummarized_chars(items: list[dict], start: int) -> int:
    return sum(len(b) + 2 for b in (message_block(i) for i in items[start:]) if b)


def build_context(store: ConversationStore, conversation_id: str) -> tuple[str, dict]:
    meta = store.get_meta(conversation_id)
    items = mark_skipped(store.load_messages(conversation_id))
    start = min(int(meta.get("summarized_through") or 0), len(items))
    blocks, first = select_recent(items, start, RECENT_BUDGET_CHARS)
    parts = []
    summary = (meta.get("summary") or "").strip()
    if summary:
        parts.append(
            f"## Long-term summary of earlier messages 1-{start} "
            f"(written by {meta.get('summary_model') or 'a model'})\n{summary}"
        )
    omitted = first - start
    if omitted > 0:
        parts.append(f"(Note: {omitted} older messages are not shown and not yet summarized.)")
    if blocks:
        parts.append("## Recent conversation (verbatim, oldest first)\n" + "\n\n".join(blocks))
    info = {"summarized_through": start, "recent_from": first, "total": len(items), "omitted": omitted}
    return ("\n\n".join(parts) if parts else "(new conversation)"), info


SUMMARY_PROMPT = """You maintain the long-term memory of a shared conversation between a user, GPT and Claude.
Merge the EXISTING SUMMARY and the NEW MESSAGES into one updated summary.

Rules:
- Write in the same language the user mostly uses (usually Korean).
- Keep these sections, as bullet points:
  1. 사용자 선호 / 작업 방식
  2. 중요한 사실·배경 정보 (names, versions, paths, numbers exactly as written)
  3. 결정 사항 (who decided what)
  4. 미해결 항목 / 다음 할 일
  5. 대화 흐름 요약 (short)
- Never drop an item from the existing summary unless the new messages clearly supersede it; then note the change.
- Attribute claims to their speaker (사용자 / GPT / Claude / Council) when it matters.
- Keep it under {max_chars} characters. Output only the summary.

EXISTING SUMMARY:
{existing}

NEW MESSAGES (messages {first}-{last}):
{messages}
"""


def _summarizer(prefer: str, gpt_model: str, claude_model: str) -> tuple[str, list[str], str]:
    if prefer == "gpt":
        return "gpt", gpt_model, "GPT" + (f" ({gpt_model})" if gpt_model and gpt_model != "account default" else "")
    return "claude", claude_model, "Claude" + (f" ({claude_model})" if claude_model and claude_model != "account default" else "")


def maybe_summarize(
    store: ConversationStore,
    conversation_id: str,
    prefer: str = "claude",
    gpt_model: str = "",
    claude_model: str = "",
    force: bool = False,
    runner=call_model,
) -> dict:
    """필요하면 장기 요약을 갱신한다. 실패해도 예외를 던지지 않는다.
    반환: {"status": "skipped"|"updated"|"failed", ...}"""
    meta = store.get_meta(conversation_id)
    items = mark_skipped(store.load_messages(conversation_id))
    start = min(int(meta.get("summarized_through") or 0), len(items))
    pending = unsummarized_chars(items, start)
    if not force and pending <= SUMMARY_TRIGGER_CHARS:
        return {"status": "skipped", "pending_chars": pending}

    # 최근 KEEP_RECENT_CHARS 분량은 원문으로 남긴다 (메시지 단위)
    _, keep_from = select_recent(items, start, KEEP_RECENT_CHARS)
    end = max(start, keep_from)
    if force and end == start:
        end = len(items)
    if end <= start:
        return {"status": "skipped", "pending_chars": pending}

    which, model, label = _summarizer(prefer, gpt_model, claude_model)
    summary = (meta.get("summary") or "").strip()
    cursor = start
    try:
        while cursor < end:
            chunk: list[str] = []
            size = 0
            chunk_start = cursor
            while cursor < end:
                block = message_block(items[cursor])
                if not block:
                    cursor += 1
                    continue
                if chunk and size + len(block) > SUMMARY_INPUT_MAX_CHARS:
                    break
                chunk.append(block[:SUMMARY_INPUT_MAX_CHARS])
                size += len(block)
                cursor += 1
            if not chunk:
                continue
            prompt = SUMMARY_PROMPT.format(
                max_chars=SUMMARY_MAX_CHARS,
                existing=summary or "(none)",
                first=chunk_start + 1,
                last=cursor,
                messages="\n\n".join(chunk),
            )
            summary = runner(which, model, prompt, "chat", None, SUMMARY_TIMEOUT_SECONDS).strip()
            # 부분 성공도 저장해 진행분을 잃지 않는다
            store.update_meta(
                conversation_id, summary=summary, summarized_through=cursor, summary_model=label,
                summary_updated_at=now(), summary_error="",
            )
    except (CliFailure, OSError) as exc:
        message = exc.details() if isinstance(exc, CliFailure) else str(exc)
        store.update_meta(conversation_id, summary_error=f"{time_label()} 요약 실패 ({label}): {message[:1500]}")
        return {"status": "failed", "error": message, "model": label}
    return {"status": "updated", "summarized_through": cursor, "model": label}


def time_label() -> str:
    return time.strftime("%Y-%m-%d %H:%M")
