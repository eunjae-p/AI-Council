"""토론(Discussion) 모드: 프롬프트와 PC 폴더 기록.

진행 순서
1라운드  GPT·Claude 가 서로의 답을 보지 않고 동시에 독립 의견을 낸다.
2라운드  각자 상대의 1라운드 답을 읽고 교차 검토(동의·반박·누락·입장 변화)를 쓴다.
결론     사회자(Claude)가 합의점·쟁점·확인 필요 항목을 구분해 최종 결론을 낸다.

기록 폴더 (Git 제외)
data/debates/<대화 생성 시각>_<대화 제목>/<번호>_<시각>/
    질문.md, 1_GPT.md, 1_Claude.md, 2_GPT_검토.md, 2_Claude_검토.md, 결론.md
"""
from __future__ import annotations

import time
from pathlib import Path

from council_store import ConversationStore, safe_filename

ROUND_LABELS = {1: "1차 의견", 2: "교차 검토"}

ROUND1_NOTE = """
## Discussion — round 1 (independent opinion)
This question is being discussed by GPT and Claude. Give your own independent, well-reasoned answer.
The other model is answering separately right now; in the next round you will each review the other's answer.
State your assumptions, give concrete recommendations, and mark anything you could not verify as "검증 필요" (needs verification).
"""

ROUND2_NOTE = """
## Discussion — round 2 (cross review)
In round 1 you and {other} answered the question independently. Both answers are below.
Review {other}'s answer critically and honestly — do not just agree to be polite. Write, in the user's language:
1. Points you agree with
2. Points you disagree with or would correct, with reasons/evidence
3. Important things {other} missed (or that you missed)
4. Your updated position after seeing {other}'s answer (say clearly if you changed your mind)
Be concise; do not repeat your whole round-1 answer.

### Your round-1 answer
{mine}

### {other}'s round-1 answer
{theirs}
"""

WEB_ON_NOTE = """
## Web search
Web search is enabled. Check facts that may have changed (products, prices, APIs, policies, terms) against
official documentation or primary sources, and cite the URLs you relied on.
"""

WEB_OFF_NOTE = """
## No web access
You cannot browse the web in this session. Do not present uncertain or time-sensitive facts as confirmed;
mark them "검증 필요" (needs verification).
"""

SYNTH_PROMPT = """You are the moderator of a discussion between GPT and Claude.
Write the final answer for the user from the material below (round-1 independent answers and round-2 cross reviews).

Structure (write headings in the user's language; for Korean use exactly these):
## 결론 — the recommended answer/decision in a few sentences
## 합의된 점 — what both models agree on
## 의견이 갈린 점 — each disagreement: who said what, which view is better supported and why (say if it is a judgment call)
## 확인이 필요한 항목 — claims neither model verified, and how the user can check them
Then add any details the user needs to act on the answer. Do not invent new facts. Output only the final answer.

Shared context:
{context}

User question:
{question}

Attached file summaries:
{attachments}

GPT — round 1:
{gpt1}

Claude — round 1:
{claude1}

GPT — round 2 review of Claude:
{gpt2}

Claude — round 2 review of GPT:
{claude2}
"""


def conversation_dir(store: ConversationStore, conversation_id: str) -> Path:
    """대화별 토론 기록 폴더. 처음 만들 때 이름을 메타에 저장해 제목을 바꿔도 같은 폴더를 쓴다."""
    meta = store.get_meta(conversation_id)
    base = store.data_dir / "debates"
    name = meta.get("debate_dir")
    if not name:
        created = time.strftime("%Y-%m-%d_%H%M", time.localtime(float(meta.get("created_at") or time.time())))
        name = safe_filename(f"{created}_{meta.get('title') or '대화'}", 70)
        candidate, n = name, 2
        while (base / candidate).exists():
            candidate = f"{name}_{n}"
            n += 1
        name = candidate
        store.update_meta(conversation_id, debate_dir=name)
    path = base / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def turn_dir(store: ConversationStore, conversation_id: str) -> Path:
    """질문 하나(토론 한 번)마다 하위 폴더: 01_204512"""
    base = conversation_dir(store, conversation_id)
    n = sum(1 for p in base.iterdir() if p.is_dir()) + 1
    path = base / f"{n:02d}_{time.strftime('%H%M%S')}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_log(folder: Path | None, filename: str, title: str, text: str, model: str = "") -> None:
    if folder is None:
        return
    head = f"# {title}\n\n_{time.strftime('%Y-%m-%d %H:%M:%S')}" + (f" · {model}" if model else "") + "_\n\n"
    try:
        (folder / filename).write_text(head + text.rstrip() + "\n", encoding="utf-8")
    except OSError:
        pass  # 기록 실패해도 토론은 계속
