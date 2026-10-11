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

# 토론 참가자 행동 지침 (1·2라운드 공통) — 서로 맞춰 주다가 함께 틀리는 것을 줄이기 위한 규칙
DISCUSSION_RULES = """
## Council discussion rules (follow strictly)
- Be analytical and dispassionate. Judge claims only by evidence and reasoning — not by who said them,
  how confident they sound, or a wish to be polite or agreeable.
- Separate clearly: verified facts (with source) / reasoned inferences / opinions or judgment calls.
- Give a confidence level (high / medium / low) for your key claims. Never invent facts, numbers, APIs or quotes.
- Do not concede a point unless you are given a better argument or evidence. If you change your mind, name
  the specific argument that changed it. If nothing new was presented, keep your position and say why.
- Do not disagree just to look independent either: agree when the reasoning is actually sound.
- The other model was trained on similar data and may share your blind spots. Agreement between you is NOT
  evidence of correctness — point out assumptions you both rely on that have not been verified.
- If the question cannot be answered reliably, say so instead of guessing.
"""

ROUND1_NOTE = DISCUSSION_RULES + """
## Discussion — round 1 (independent opinion)
This question is being discussed by GPT and Claude. Give your own independent, well-reasoned answer.
The other model is answering separately right now; in the next round you will each review the other's answer.
State your assumptions, give concrete recommendations, and mark anything you could not verify as "검증 필요" (needs verification).
"""

ROUND2_NOTE = DISCUSSION_RULES + """
## Discussion — round 2 (cross review)
In round 1 you and {other} answered the question independently. Both answers are below.
Review {other}'s answer critically and dispassionately, following the rules above. Write, in the user's language:
1. Points you agree with — only where the reasoning holds up, and why
2. Points you disagree with or would correct — with reasons/evidence and your confidence
3. Important things {other} missed (or that you missed)
4. Assumptions you BOTH made that are still unverified
5. Your updated position — what changed and which argument changed it, or "no change" and why
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

# 최종 정리: 정리하는 모델이 자기 답을 편들지 않도록 이름을 가린 채(모델 A/B) 정리하게 하고,
# 결과의 "모델 A/B" 를 실제 이름으로 바꿔 보여 준다. 어느 쪽이 A 인지는 매번 무작위.
SYNTH_PROMPT = """You are a strictly neutral moderator of a discussion between two AI models, "모델 A" and "모델 B".
You do not know which model is which, and you must not try to guess. Treat both equally.
Write the final answer for the user from the material below (round-1 independent answers and round-2 cross reviews).

Moderator rules:
- Decide each point by the quality of evidence and reasoning only — not by length, confidence, tone or which model said it.
- Do not add your own new claims or facts; you may only weigh and organize what the two models said.
  If both missed something obvious, list it under "확인이 필요한 항목" instead of asserting it.
- A point both models agree on is not automatically correct: if it rests on an unverified assumption, say so.
- When a disagreement cannot be settled from the material, say it is unresolved and what would settle it.
- Refer to the models only as "모델 A" and "모델 B" (exactly these labels).

Structure (write headings in the user's language; for Korean use exactly these):
## 결론 — the recommended answer/decision in a few sentences, with overall confidence (높음/보통/낮음)
## 합의된 점 — what both models agree on (flag any that rest on unverified assumptions)
## 의견이 갈린 점 — each disagreement: what 모델 A and 모델 B said, which is better supported and why, or "미결"
## 확인이 필요한 항목 — claims neither model verified, and how the user can check them
Then add any details the user needs to act on the answer. Output only the final answer.

Shared context:
{context}

User question:
{question}

Attached file summaries:
{attachments}

모델 A — round 1:
{a1}

모델 B — round 1:
{b1}

모델 A — round 2 review of 모델 B:
{a2}

모델 B — round 2 review of 모델 A:
{b2}
"""

_LABEL_FORMS = ("모델 {x}", "모델{x}", "Model {x}")


def blind_synth_prompt(rng, **kw) -> tuple[str, dict[str, str]]:
    """GPT/Claude 를 무작위로 모델 A/B 에 배정한 정리 프롬프트와 배정표를 돌려준다."""
    order = ["GPT", "Claude"]
    rng.shuffle(order)
    mapping = {"A": order[0], "B": order[1]}
    key = {"GPT": "gpt", "Claude": "claude"}
    prompt = SYNTH_PROMPT.format(
        context=kw["context"], question=kw["question"], attachments=kw["attachments"],
        a1=kw[key[mapping["A"]] + "1"], b1=kw[key[mapping["B"]] + "1"],
        a2=kw[key[mapping["A"]] + "2"], b2=kw[key[mapping["B"]] + "2"],
    )
    return prompt, mapping


def unblind(text: str, mapping: dict[str, str]) -> str:
    """정리문의 '모델 A/B' 를 실제 모델 이름으로 바꾼다."""
    for letter, name in mapping.items():
        for form in _LABEL_FORMS:
            text = text.replace(form.format(x=letter), name)
    return text


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
