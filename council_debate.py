"""토론(Discussion) 모드: 프롬프트·결론 카드·PC 폴더 기록.

진행 순서 (V0.28.0)
  [작성 요청] "프롬프트 써줘·작성해줘·다듬어줘·번역해줘…" (classify == "write", 대화 모드만)
      초안(한 모델) → 검토·개선(다른 모델) → 끝 (2회)
      검토자가 방향 자체가 틀렸다고 보면(verdict: major) → 초안 작성자 답변 → 사회자 결론 (4회)
  [토론]
      1라운드  GPT·Claude 가 서로의 답을 보지 않고 독립 의견 (2회)
      쟁점 정리 사회자가 두 답을 비교 → 쟁점 없음: 이 호출이 바로 최종 결론 (총 3회, 절약 모드와 무관)
                                     → 쟁점 있음: 쟁점 목록 (💰 절약 모드면 여기서 결론까지)
      2라운드  쟁점만 교차 반박, 쟁점마다 입장(keep/partial/concede) 표시 (2회)
      3라운드  둘 다 입장을 유지한 쟁점만 마지막 반박 (2회, 미결일 때만)
      결론     사회자가 최종 결론 카드 (1회) → 총 6회, 미결이면 8회
  사회자: 질문마다 GPT·Claude 가 번갈아 맡고, 이름을 가린 채(모델 A/B, 무작위) 핵심 주장 목록 위주로 판단.
  결론 카드(JSON): 결론·신뢰도 / 결과물 / 다음에 할 일 / 정해 주셔야 할 것 / 직접 확인할 것 / 근거(접힘)

기록 폴더 (Git 제외)
  data/debates/<대화 생성 시각>_<대화 제목>/<번호>_<시각>/
      질문.md, 1_GPT.md, 1_Claude.md, 쟁점.md, 2_*_반박.md, 3_*_최종반박.md, 결론.md  (작성: 초안·검토 파일)
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

from council_store import ConversationStore, safe_filename

ROUND_LABELS = {1: "1차 의견", 2: "쟁점 반박", 6: "마지막 반박", 7: "쟁점 정리"}

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
End with a section headed exactly "## 핵심 주장" listing your key claims, one per line, in this form:
- [확신도: 높음|보통|낮음] claim
"""

ROUND2_NOTE = DISCUSSION_RULES + """
## Discussion — round 2 (disputed points only)
In round 1 you and {other} answered independently. A neutral moderator found that you agree on everything except the
points below. Discuss ONLY these points — do not repeat what you agreed on. For each point, in the user's language:
- your position and the strongest reason/evidence for it, and what in {other}'s position is right or wrong
- whether you keep your position, partly agree, or concede (and which argument changed your mind)
Be concise.

### Disputed points
{disputes}

End with this block (one line per point number, value keep | partial | concede):
```stance
1: keep
```
"""

ROUND3_NOTE = DISCUSSION_RULES + """
## Discussion — round 3 (final, unresolved points only)
After round 2 you and {other} still disagree on the points below. This is the last round.
For each point: give any NEW argument or evidence (do not repeat round 2). If you have nothing new, keep your position
and say so. Then state exactly what would settle the question (a test, a source, a decision the user must make).
If web search is available, try to verify the facts now.

### Unresolved points (with both round-2 replies)
{disputes}

### {other}'s round-2 reply
{theirs}

End with the same stance block:
```stance
1: keep
```
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

# ---------------- 사회자 (질문마다 GPT·Claude 교대, 이름은 모델 A/B 로 가림) ----------------

MODERATOR_RULES = """You are a strictly neutral moderator of a discussion between two AI models, "모델 A" and "모델 B".
You do not know which model is which, and you must not try to guess. One of them may be you — ignore that.
- Judge mainly by each model's "핵심 주장" list (claims with confidence); use the full answers only for details.
- Decide each point by the quality of evidence and reasoning only — not by length, confidence, tone or who said it.
- Do not add new claims or facts of your own; only weigh and organize what the two models said.
- A point both models agree on is not automatically correct: if it rests on an unverified assumption, say so.
- Refer to the models only as "모델 A" and "모델 B". Write all text in the user's language.
"""

CARD_SPEC = """Final conclusion card — output ONE JSON object in a ```json fenced block, with these keys:
{
  "conclusion": "the answer/decision in at most 3 short sentences",
  "confidence": "높음 | 보통 | 낮음",
  "actions": [{"text": "one concrete next step for the user, one line", "work": true}],
  "decisions": [{"topic": "...", "options": ["...", "..."], "recommend": "...", "why": "one line"}],
  "checks": [{"item": "unverified claim", "how": "how the user can check it"}],
  "agreed": ["what both models agree on, one line each"],
  "disputed": [{"topic": "...", "A": "모델 A's view", "B": "모델 B's view", "verdict": "which is better supported and why, or 미결"}]
}
Rules for the card:
- "actions": at most 5, ordered, each one line, starting with a verb. "work": true only for steps that edit files or run
  commands/tools on the user's computer. Empty list if there is nothing to do.
- "decisions": only choices the USER must make (unresolved disputes, trade-offs). Empty list if none.
- "checks": only things that need verification. Empty list if none.
- Keep every string short. No markdown headings inside strings.
If the user asked for a piece of content (a prompt, text, translation, code, plan document...), put the complete final
content AFTER the JSON block, between a line <<<DELIVERABLE>>> and a line <<<END>>>. Do not put it inside the JSON.
Answer with nothing else.
"""

ANALYZE_PROMPT = MODERATOR_RULES + """
Below are round-1 answers that 모델 A and 모델 B wrote independently.
Task: compare them and decide whether they substantially agree.
- Minor differences in wording, detail or order are NOT disagreements. A disagreement is a different recommendation,
  a contradictory fact, or a different judgment that would change what the user does.
{saver_rule}
Output:
1. A ```json block: {{"status": "agreed" | "disputed", "disputes": [{{"topic": "...", "A": "...", "B": "..."}}]}}
   ("disputes" empty when agreed; at most 5, most important first.)
2. {final_rule}

""" + CARD_SPEC.replace("{", "{{").replace("}", "}}") + """
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
"""

FINAL_PROMPT = MODERATOR_RULES + """
Write the final conclusion card from the discussion below (round-1 answers, the disputed points, and the replies on them).
Settle each disputed point by evidence; if it cannot be settled, put it in "decisions" (what the user must choose, with
your recommendation) or "checks" (what to verify), and mark it 미결 in "disputed".

""" + CARD_SPEC.replace("{", "{{").replace("}", "}}") + """
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

Disputed points:
{disputes}

모델 A — replies on the disputed points:
{a2}

모델 B — replies on the disputed points:
{b2}
"""

ANALYZE_FINAL_ALWAYS = 'Then ALWAYS write the final conclusion card (token saver mode: there will be no further rounds; put disputes in "decisions" or mark them 미결).'
ANALYZE_FINAL_IF_AGREED = 'ONLY if status is "agreed", then write the final conclusion card. If "disputed", stop after the first JSON block.'


def _blind(rng, gpt: str, claude: str) -> tuple[str, str, dict[str, str]]:
    order = ["GPT", "Claude"]
    rng.shuffle(order)
    mapping = {"A": order[0], "B": order[1]}
    by = {"GPT": gpt, "Claude": claude}
    return by[mapping["A"]], by[mapping["B"]], mapping


def analyze_prompt(rng, *, context, question, attachments, gpt1, claude1, saver) -> tuple[str, dict[str, str]]:
    a1, b1, mapping = _blind(rng, gpt1, claude1)
    prompt = ANALYZE_PROMPT.format(
        saver_rule="", final_rule=ANALYZE_FINAL_ALWAYS if saver else ANALYZE_FINAL_IF_AGREED,
        context=context, question=question, attachments=attachments, a1=a1, b1=b1)
    return prompt, mapping


def final_prompt(mapping, *, context, question, attachments, gpt1, claude1, disputes, gpt2, claude2) -> str:
    by1 = {"GPT": gpt1, "Claude": claude1}
    by2 = {"GPT": gpt2, "Claude": claude2}
    return FINAL_PROMPT.format(context=context, question=question, attachments=attachments,
                               a1=by1[mapping["A"]], b1=by1[mapping["B"]], disputes=disputes,
                               a2=by2[mapping["A"]], b2=by2[mapping["B"]])


def _json_blocks(text: str) -> list[dict]:
    """```json 블록(없으면 본문의 { … }) 을 순서대로 파싱."""
    out = []
    for m in re.finditer(r"```(?:json)?\s*\n(.*?)\n```", text, re.S):
        try:
            v = json.loads(m.group(1))
            if isinstance(v, dict):
                out.append(v)
        except ValueError:
            continue
    if not out:
        start = text.find("{")
        while start != -1:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            v = json.loads(text[start:i + 1])
                            if isinstance(v, dict):
                                out.append(v)
                        except ValueError:
                            pass
                        break
            start = text.find("{", i + 1 if depth == 0 else start + 1)
            if len(out) >= 2:
                break
    return out


def deliverable(text: str) -> str:
    m = re.search(r"<<<DELIVERABLE>>>\s*\n(.*?)\n?\s*<<<END>>>", text, re.S)
    if m:
        return m.group(1).strip()
    m = re.search(r"<<<DELIVERABLE>>>\s*\n(.*)$", text, re.S)  # END 를 빠뜨린 경우
    return m.group(1).strip() if m else ""


def _strs(v, n: int) -> list:
    return [x for x in (v if isinstance(v, list) else [])][:n]


def normalize_card(raw: dict, text: str) -> dict | None:
    if not isinstance(raw, dict) or not str(raw.get("conclusion") or "").strip():
        return None
    conf = str(raw.get("confidence") or "").strip()
    conf = {"high": "높음", "medium": "보통", "low": "낮음"}.get(conf.lower(), conf)
    card = {
        "conclusion": str(raw["conclusion"]).strip(),
        "confidence": conf if conf in ("높음", "보통", "낮음") else "보통",
        "actions": [{"text": str(a.get("text") if isinstance(a, dict) else a).strip(),
                     "work": bool(a.get("work")) if isinstance(a, dict) else False}
                    for a in _strs(raw.get("actions"), 5) if str(a.get("text") if isinstance(a, dict) else a).strip()],
        "decisions": [d for d in _strs(raw.get("decisions"), 5) if isinstance(d, dict) and d.get("topic")],
        "checks": [c for c in _strs(raw.get("checks"), 6) if isinstance(c, dict) and c.get("item")],
        "agreed": [str(x) for x in _strs(raw.get("agreed"), 10) if str(x).strip()],
        "disputed": [d for d in _strs(raw.get("disputed"), 6) if isinstance(d, dict) and d.get("topic")],
    }
    body = deliverable(text)
    if body:
        card["deliverable"] = body
    return card


def parse_analysis(text: str) -> tuple[str, list[dict], dict | None]:
    """쟁점 정리 결과 → (status, disputes, card 또는 None). 형식이 틀리면 ("", [], None)."""
    blocks = _json_blocks(text)
    status, disputes, card = "", [], None
    for b in blocks:
        if "status" in b and not status:
            status = "disputed" if str(b.get("status")).lower().startswith("disput") else "agreed"
            disputes = [d for d in _strs(b.get("disputes"), 5) if isinstance(d, dict) and d.get("topic")]
        elif "conclusion" in b and card is None:
            card = normalize_card(b, text)
    if status == "disputed" and not disputes:
        status = "agreed"
    return status, disputes, card


def parse_card(text: str) -> dict | None:
    for b in _json_blocks(text):
        if "conclusion" in b:
            return normalize_card(b, text)
    return None


def disputes_text(disputes: list[dict], names: dict[str, str] | None = None) -> str:
    """쟁점 목록 → 번호 붙은 글. names: {"A": "GPT", "B": "Claude"} 이면 실제 이름으로."""
    a = (names or {}).get("A", "모델 A")
    b = (names or {}).get("B", "모델 B")
    return "\n".join(f"{i}. {d.get('topic')}\n   - {a}: {d.get('A', '')}\n   - {b}: {d.get('B', '')}"
                     for i, d in enumerate(disputes, 1))


def parse_stance(text: str) -> dict[int, str]:
    m = re.search(r"```stance\s*\n(.*?)```", text, re.S)
    body = m.group(1) if m else text[-400:]
    out = {}
    for n, v in re.findall(r"(?m)^\s*(\d+)\s*[:.)]\s*(keep|partial|concede)\b", body, re.I):
        out[int(n)] = v.lower()
    return out


def unresolved(gpt_text: str, claude_text: str, count: int) -> list[int]:
    """두 모델 모두 'keep' 인 쟁점 번호 (표시가 없으면 해결로 본다)."""
    g, c = parse_stance(gpt_text), parse_stance(claude_text)
    return [i for i in range(1, count + 1) if g.get(i) == "keep" and c.get(i) == "keep"]


CARD_HEAD = {
    "ko": {"conclusion": "✅ 결론", "conf": "신뢰도", "deliverable": "📄 결과물", "actions": "👉 다음에 할 일",
           "decisions": "⚖️ 정해 주셔야 할 것", "checks": "🔍 직접 확인할 것", "details": "근거",
           "agreed": "합의된 점", "disputed": "의견이 갈린 점", "recommend": "추천", "how": "확인 방법"},
    "en": {"conclusion": "✅ Conclusion", "conf": "confidence", "deliverable": "📄 Result", "actions": "👉 Next steps",
           "decisions": "⚖️ Decisions for you", "checks": "🔍 Things to verify", "details": "Details",
           "agreed": "Agreed", "disputed": "Disagreements", "recommend": "recommended", "how": "how to check"},
}
CONF_EN = {"높음": "high", "보통": "medium", "낮음": "low"}


def card_markdown(card: dict, lang: str = "ko") -> str:
    """결론 카드 → Markdown (저장·맥락·내보내기용. 화면은 카드로 그린다)."""
    h = CARD_HEAD["en" if lang == "en" else "ko"]
    conf = CONF_EN.get(card["confidence"], card["confidence"]) if lang == "en" else card["confidence"]
    out = [f"## {h['conclusion']} ({h['conf']}: {conf})", card["conclusion"]]
    if card.get("deliverable"):
        out += ["", f"## {h['deliverable']}", card["deliverable"]]
    if card.get("actions"):
        out += ["", f"## {h['actions']}"] + [f"{i}. {a['text']}" for i, a in enumerate(card["actions"], 1)]
    if card.get("decisions"):
        out += ["", f"## {h['decisions']}"]
        for d in card["decisions"]:
            opts = " vs ".join(str(o) for o in d.get("options") or [])
            rec = f" → {h['recommend']}: {d['recommend']}" if d.get("recommend") else ""
            why = f" — {d['why']}" if d.get("why") else ""
            out.append(f"- **{d['topic']}**" + (f": {opts}" if opts else "") + rec + why)
    if card.get("checks"):
        out += ["", f"## {h['checks']}"] + [f"- {c['item']}" + (f" ({h['how']}: {c['how']})" if c.get("how") else "")
                                            for c in card["checks"]]
    if card.get("agreed") or card.get("disputed"):
        out += ["", f"### {h['details']}"]
        if card.get("agreed"):
            out += [f"**{h['agreed']}**"] + [f"- {x}" for x in card["agreed"]]
        if card.get("disputed"):
            out += [f"**{h['disputed']}**"] + [f"- {d['topic']}: A) {d.get('A', '')} / B) {d.get('B', '')}"
                                               + (f" → {d['verdict']}" if d.get("verdict") else "") for d in card["disputed"]]
    return "\n".join(out).strip()


# ---------------- 작성 요청: 초안 → 검토·개선 ----------------

_WRITE_PATTERNS = [
    r"프롬프트", r"(써|작성해|만들어|짜)\s*(줘|주세요|줄래|줄 수)", r"작성\s*(해|좀|부탁)", r"다듬어", r"고쳐\s*(써|줘)",
    r"번역(해|좀|부탁)", r"(으로|로)\s*번역", r"요약해", r"초안", r"문구", r"카피\s*(써|만들)", r"(메일|이메일|공지|보고서|기획서|소개글|자기소개서)\s*(을|를)?\s*(써|작성)",
    r"\b(write|draft|rewrite|polish|translate|proofread|summari[sz]e)\b", r"\bprompt\b",
]
_DISCUSS_HINTS = [r"어느\s*(게|것이|쪽)", r"뭐가\s*(나|좋|맞)", r"비교", r"왜\s", r"맞(아|나|는지)", r"추천", r"장단점", r"vs\.?\b",
                  r"\b(which|why|compare|should i|versus)\b"]


def classify(question: str) -> str:
    """'write'(결과물 작성 요청) 또는 'discuss'. 판단·비교 질문이 섞이면 토론으로."""
    q = question.strip().lower()
    if not q:
        return "discuss"
    if any(re.search(p, q) for p in _DISCUSS_HINTS):
        return "discuss"
    return "write" if any(re.search(p, q) for p in _WRITE_PATTERNS) else "discuss"


WRITE_DRAFT_NOTE = """
## Writing task — draft
The user asked for a piece of content. Write the complete content now, ready to use (not a plan, not options).
Keep any explanation to one or two lines after it. {other} will review and improve your draft next.
"""

WRITE_REVIEW_NOTE = """
## Writing task — review and improve
{other} wrote the draft below for the user's request. Improve it: fix errors, gaps and unclear parts, keep what works,
follow the user's request exactly. Then output, in the user's language, exactly these sections:
<<<FINAL>>>
(the complete improved final version, ready to use)
<<<CHANGES>>>
- one line per change and why (at most 5)
<<<VERDICT>>>
ok — if the draft's direction was right (you only improved it)
major — only if the draft's whole approach is wrong for the request; then add one line: <<<ISSUE>>> what is wrong

### Draft by {other}
{draft}
"""

WRITE_RESPOND_NOTE = DISCUSSION_RULES + """
## Writing task — reply to the review
You wrote the draft below. {other} reviewed it and says the approach is wrong (issue below) and wrote another version.
Answer briefly: do you agree? Keep your approach only with a concrete reason. Then give your best final version.

### Issue raised by {other}
{issue}

### Your draft
{draft}

### {other}'s version
{theirs}
"""

WRITE_FINAL_PROMPT = MODERATOR_RULES + """
The user asked for a piece of content. 모델 A and 모델 B disagree on the approach. Choose the better version (or combine
them) and put the complete final content in the deliverable section. Explain the choice in the card.

""" + CARD_SPEC.replace("{", "{{").replace("}", "}}") + """
Shared context:
{context}

User request:
{question}

모델 A's version and reasoning:
{a}

모델 B's version and reasoning:
{b}
"""


def parse_review(text: str) -> tuple[str, list[str], str, str]:
    """검토 결과 → (최종본, 바꾼 점, verdict ok|major, issue). 형식이 없으면 전체를 최종본으로."""
    def sec(name: str) -> str:
        m = re.search(rf"<<<{name}>>>\s*\n?(.*?)(?=\n?<<<[A-Z]+>>>|$)", text, re.S)
        return m.group(1).strip() if m else ""
    final = sec("FINAL") or text.strip()
    changes = [ln.lstrip("-• ").strip() for ln in sec("CHANGES").splitlines() if ln.strip()][:5]
    verdict = "major" if sec("VERDICT").lower().startswith("major") else "ok"
    return final, changes, verdict, sec("ISSUE")


_LABEL_FORMS = ("모델 {x}", "모델{x}", "Model {x}")


def blind_names(text: str, mapping: dict[str, str]) -> str:
    """사회자에게 넘기는 반박 글 속 'GPT'·'Claude' 를 모델 A/B 로 (토론자는 서로를 실제 이름으로 부르므로).
    'Claude Code'·'GPT-5' 처럼 제품 이름에 붙은 경우는 그대로 둔다."""
    for letter, name in mapping.items():
        text = re.sub(rf"(?<![A-Za-z0-9_-]){name}(?![A-Za-z0-9_-]| Code| Desktop| CLI)", f"모델 {letter}", text)
    return text


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
