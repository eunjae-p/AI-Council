"""ComfyUI 워크플로우 JSON 파서.

모델에게 원본 JSON을 통째로 읽히기 전에, 코드로 확실하게 뽑을 수 있는 정보를 먼저 정리한다.
- 형식: UI 형식(nodes/links, 프런트엔드 저장 파일) 또는 API 형식({id: {class_type, inputs}})
- 노드: 타입, 제목, 상태(활성/음소거/바이패스), 그룹, 위젯 값
- 색상 등급(팀 규칙): 빨강 = MUST(필수 입력·웹UI 노출), 노랑/주황 = SHOULD(선택 노출), 그 외 = 일반
  색상 판정 제외: MarkdownNote, Note, Label (rgthree), SetNode, GetNode
- 모델 파일, 커스텀 노드 팩(cnr_id / aux_id), 서브그래프
표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

MODEL_EXT = re.compile(r"\.(safetensors|ckpt|pt|pth|gguf|bin|onnx|sft|pkl)$", re.IGNORECASE)
COLOR_EXCLUDED = {"MarkdownNote", "Note", "Label (rgthree)", "SetNode", "GetNode", "PrimitiveNode"}
COLOR_EXCLUDED_LOWER = {t.lower() for t in COLOR_EXCLUDED}
MODES = {0: "활성", 1: "트리거", 2: "음소거", 4: "바이패스"}

# LiteGraph 기본 팔레트 (color, bgcolor)
PALETTE = {
    "red": ("#322", "#533"), "brown": ("#332922", "#593930"), "green": ("#232", "#353"),
    "blue": ("#223", "#335"), "pale_blue": ("#2a363b", "#3f5159"), "cyan": ("#233", "#355"),
    "purple": ("#323", "#535"), "yellow": ("#432", "#653"), "black": ("#222", "#000"),
}
PALETTE_KO = {"red": "빨강", "brown": "갈색(주황)", "green": "초록", "blue": "파랑", "pale_blue": "연파랑",
              "cyan": "청록", "purple": "보라", "yellow": "노랑", "black": "검정", "custom": "사용자 지정"}
GRADE_BY_PALETTE = {"red": "MUST", "yellow": "SHOULD", "brown": "SHOULD"}


def _norm_hex(value: str) -> str:
    value = (value or "").strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", value):
        value = "#" + "".join(c * 2 for c in value[1:])
    return value


_PALETTE_LOOKUP = {}
for _name, (_c, _bg) in PALETTE.items():
    _PALETTE_LOOKUP[_norm_hex(_c)] = _name
    _PALETTE_LOOKUP[_norm_hex(_bg)] = _name


def color_info(node: dict) -> tuple[str, str]:
    """(색 이름, 등급). 색이 없으면 ('', '일반')."""
    raw = node.get("bgcolor") or node.get("color") or ""
    if not raw:
        return "", "일반"
    name = _PALETTE_LOOKUP.get(_norm_hex(raw))
    if name:
        return PALETTE_KO[name], GRADE_BY_PALETTE.get(name, "일반")
    # 사용자 지정 색: 색상(hue)으로 추정
    hexv = _norm_hex(raw)
    if re.fullmatch(r"#[0-9a-f]{6}", hexv):
        r, g, b = (int(hexv[i:i + 2], 16) / 255 for i in (1, 3, 5))
        mx, mn = max(r, g, b), min(r, g, b)
        if mx - mn > 0.08:
            if mx == r:
                hue = (60 * ((g - b) / (mx - mn))) % 360
            elif mx == g:
                hue = 60 * ((b - r) / (mx - mn)) + 120
            else:
                hue = 60 * ((r - g) / (mx - mn)) + 240
            if hue < 15 or hue >= 340:
                return f"사용자 지정 {raw} (빨강 계열)", "MUST"
            if hue < 70:
                return f"사용자 지정 {raw} (주황·노랑 계열)", "SHOULD"
    return f"사용자 지정 {raw}", "일반"


def _short(value, limit: int = 80) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False)
    else:
        text = str(value)
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _widget_values(node: dict) -> list:
    values = node.get("widgets_values")
    if isinstance(values, dict):  # VideoHelperSuite 등은 dict 형식
        return [f"{k}={_short(v, 60)}" for k, v in values.items() if not isinstance(v, dict)]
    if isinstance(values, list):
        return values
    return []


def _models_in(values) -> list[str]:
    found = []

    def walk(v):
        if isinstance(v, str):
            name = v.strip()
            if MODEL_EXT.search(name):
                found.append(name)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(values)
    return found


def _pack(node: dict) -> str:
    props = node.get("properties") or {}
    cnr = props.get("cnr_id")
    aux = props.get("aux_id")
    if cnr:
        return str(cnr)
    if aux:
        return f"{aux} (aux_id)"
    return ""


def _group_of(node: dict, groups: list[dict]) -> str:
    pos = node.get("pos")
    if isinstance(pos, dict):
        pos = [pos.get("0", 0), pos.get("1", 0)]
    if not isinstance(pos, (list, tuple)) or len(pos) < 2:
        return ""
    x, y = pos[0], pos[1]
    best = ""
    best_area = None
    for g in groups:
        b = g.get("bounding") or []
        if len(b) == 4 and b[0] <= x <= b[0] + b[2] and b[1] <= y <= b[1] + b[3]:
            area = b[2] * b[3]
            if best_area is None or area < best_area:  # 가장 안쪽 그룹
                best, best_area = str(g.get("title", "")), area
    return best


def is_workflow(data) -> bool:
    if isinstance(data, dict) and isinstance(data.get("nodes"), list):
        return True
    if isinstance(data, dict) and data and all(isinstance(v, dict) and "class_type" in v for v in data.values()):
        return True
    return False


def _ui_nodes(data: dict) -> tuple[list[dict], dict[str, str]]:
    """최상위 노드 + 서브그래프 노드. 반환: (노드 목록, 서브그래프 id→이름)"""
    nodes = []
    subgraphs = {}
    for n in data.get("nodes") or []:
        if isinstance(n, dict):
            nodes.append({**n, "_scope": ""})
    for sg in ((data.get("definitions") or {}).get("subgraphs") or []):
        if not isinstance(sg, dict):
            continue
        sg_name = str(sg.get("name") or sg.get("id") or "subgraph")
        subgraphs[str(sg.get("id"))] = sg_name
        for n in sg.get("nodes") or []:
            if isinstance(n, dict):
                nodes.append({**n, "_scope": sg_name, "_groups": sg.get("groups") or []})
    return nodes, subgraphs


def summarize(data, name: str = "workflow.json", max_chars: int = 20000) -> str:
    if not is_workflow(data):
        return ""
    lines: list[str] = []
    if isinstance(data.get("nodes"), list):
        fmt = "UI 형식 (ComfyUI 프런트엔드 저장 파일)"
        nodes, subgraphs = _ui_nodes(data)
        groups = [g for g in data.get("groups") or [] if isinstance(g, dict)]
        links = data.get("links") or []
    else:  # API 형식
        fmt = "API 형식 (prompt / 실행용)"
        subgraphs, groups, links = {}, [], []
        nodes = []
        for nid, v in data.items():
            inputs = v.get("inputs") or {}
            nodes.append({
                "id": nid, "type": v.get("class_type"), "title": (v.get("_meta") or {}).get("title", ""),
                "widgets_values": [f"{k}={_short(x, 60)}" for k, x in inputs.items() if not isinstance(x, list)],
                "_api_inputs": inputs, "_scope": "", "mode": 0,
            })

    mode_count = Counter(MODES.get(n.get("mode", 0), str(n.get("mode"))) for n in nodes)
    lines.append(f"# 워크플로우 요약: {name}")
    lines.append(f"- 형식: {fmt}")
    lines.append(
        f"- 노드 {len(nodes)}개 (" + ", ".join(f"{k} {v}" for k, v in mode_count.items()) + ")"
        + (f" · 링크 {len(links)}개" if links else "")
        + (f" · 그룹 {len(groups)}개" if groups else "")
        + (f" · 서브그래프 {len(subgraphs)}개" if subgraphs else "")
    )

    graded = defaultdict(list)
    models = []
    packs: dict[str, Counter] = defaultdict(Counter)
    group_members = defaultdict(list)
    node_lines = []

    for n in nodes:
        ntype = str(n.get("type") or "?")
        if ntype in subgraphs:
            ntype = f"서브그래프[{subgraphs[ntype]}]"
        nid = n.get("id")
        title = str(n.get("title") or "")
        scope = n.get("_scope") or ""
        ref = f"#{nid}" + (f"@{scope}" if scope else "")
        state = MODES.get(n.get("mode", 0), str(n.get("mode")))
        group = _group_of(n, n["_groups"] if "_groups" in n else groups) if not n.get("_api_inputs") else ""
        values = _widget_values(n)
        val_text = ", ".join(_short(v, 50) for v in values[:8]) + (" …" if len(values) > 8 else "")
        label = f"{ref} {ntype}" + (f' "{title}"' if title and title != ntype else "")

        if ntype.lower() not in COLOR_EXCLUDED_LOWER:
            cname, grade = color_info(n)
            if grade in ("MUST", "SHOULD"):
                graded[grade].append(f"{label} [{cname}]" + (f" · 그룹 {group}" if group else "")
                                     + (f" · {state}" if state != "활성" else "") + (f" · 값: {val_text}" if val_text else ""))
        else:
            cname = ""
        for m in _models_in(n.get("_api_inputs") or n.get("widgets_values")):
            models.append(f"{m} ← {label}")
        pack = _pack(n)
        if not n.get("_api_inputs"):
            packs[pack or "(출처 표시 없음)"][ntype] += 1
        if group:
            group_members[group].append(ref)
        node_lines.append(
            f"- {label}" + (f" · {state}" if state != "활성" else "") + (f" · 그룹 {group}" if group else "")
            + (f" · 색 {cname}" if cname else "") + (f" · 값: {val_text}" if val_text else "")
        )

    lines.append("")
    lines.append("## 색상 등급 (팀 규칙: 빨강=MUST 필수 입력·웹UI 노출 / 노랑·주황=SHOULD 선택 노출 / 그 외=일반)")
    lines.append("색상 판정 제외 노드: " + ", ".join(sorted(COLOR_EXCLUDED)))
    if fmt.startswith("API"):
        lines.append("- API 형식 파일에는 노드 색상 정보가 없습니다. UI 형식으로 저장한 파일을 첨부하면 등급을 확인할 수 있습니다.")
    for grade in (() if fmt.startswith("API") else ("MUST", "SHOULD")):
        lines.append(f"### {grade} ({len(graded[grade])}개)")
        lines.extend(f"- {x}" for x in graded[grade]) if graded[grade] else lines.append("- 없음")

    lines.append("")
    lines.append(f"## 모델 파일 ({len(models)}개)")
    lines.extend(f"- {m}" for m in models) if models else lines.append("- 위젯 값에서 모델 파일명을 찾지 못함")

    if packs:
        lines.append("")
        lines.append("## 노드 팩 (properties.cnr_id / aux_id 기준)")
        for pack, types in sorted(packs.items(), key=lambda kv: (kv[0] == "comfy-core", kv[0])):
            total = sum(types.values())
            detail = ", ".join(f"{t}×{c}" if c > 1 else t for t, c in types.most_common(12))
            lines.append(f"- **{pack}** ({total}개): {detail}")

    if group_members:
        lines.append("")
        lines.append("## 그룹")
        for g, refs in group_members.items():
            lines.append(f"- {g}: {', '.join(refs)}")

    lines.append("")
    lines.append("## 노드 목록")
    lines.extend(node_lines)

    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[: max_chars - 200].rsplit("\n", 1)[0] + f"\n… (요약이 길어 {len(text) - max_chars + 200:,}자 생략. 원본 JSON 참고)"
    return text


def summarize_text(content: str, name: str) -> str:
    """파일 내용(문자열)이 ComfyUI 워크플로우면 요약, 아니면 빈 문자열."""
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return ""
    return summarize(data, name)
