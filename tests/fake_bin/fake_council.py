"""가짜 Claude·Codex 가 V0.28.0 토론(사회자·쟁점 반박·작성 검토) 프롬프트에 답하는 공통 부분.
질문에 넣는 표시: DISPUTE(쟁점 2개) · KEEP(2라운드에서도 입장 유지 → 3라운드) · MAJOR(작성 검토가 방향 반대) · BADJSON(사회자가 형식 무시)"""
import json


def card(deliver=False):
    c = {"conclusion": "모델 A 의견이 더 타당합니다. 노드를 분리하세요.", "confidence": "high",
         "actions": [{"text": "워크플로우에 노드 추가", "work": True}, {"text": "결과 비교", "work": False}],
         "decisions": [{"topic": "해상도", "options": ["1024", "2048"], "recommend": "1024", "why": "빠름"}],
         "checks": [{"item": "노드 지원 버전", "how": "릴리스 노트"}],
         "agreed": ["둘 다 분리 찬성"], "disputed": [{"topic": "해상도", "A": "1024", "B": "2048", "verdict": "미결"}]}
    out = "```json\n" + json.dumps(c, ensure_ascii=False) + "\n```"
    if deliver:
        out += "\n<<<DELIVERABLE>>>\n최종 결과물 본문\n<<<END>>>"
    return out


def answer(p):
    """V0.28 토론 프롬프트면 답을 돌려주고, 아니면 None."""
    if "moderator of a discussion" in p:
        if "BADJSON" in p:
            return "Council 결론입니다 · 모델 A 의견이 더 타당 (형식 없음)"
        if "decide whether they substantially agree" in p:
            disputed = "DISPUTE" in p
            head = {"status": "disputed" if disputed else "agreed",
                    "disputes": [{"topic": "해상도", "A": "1024 권장", "B": "2048 권장"},
                                 {"topic": "노드 순서", "A": "먼저", "B": "나중"}] if disputed else []}
            out = "```json\n" + json.dumps(head, ensure_ascii=False) + "\n```"
            if not disputed or "ALWAYS write the final" in p:
                out += "\n" + card()
            return out
        return card(deliver="User request:" in p)
    if "round 2 (disputed points only)" in p or "round 3 (final" in p:
        v = "keep" if "KEEP" in p else "concede"
        return "쟁점 반박입니다\n```stance\n1: %s\n2: concede\n```" % v
    if "Writing task — review and improve" in p:
        tail = "major\n<<<ISSUE>>> 방향이 틀림" if "MAJOR" in p else "ok"
        return "<<<FINAL>>>\n다듬은 최종본\n<<<CHANGES>>>\n- 문장 정리\n<<<VERDICT>>>\n" + tail
    if "Writing task — reply to the review" in p:
        return "검토에 대한 답변과 수정본"
    if "Writing task — draft" in p:
        return "초안 본문"
    return None
