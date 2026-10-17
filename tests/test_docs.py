"""문서의 버전 표기가 실제 버전과 같은지 검사 (README 제목에 옛 버전이 남는 문제 방지).
실행: python tests/test_docs.py
"""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
read = lambda n: (ROOT / n).read_text(encoding="utf-8")
version = re.search(r'^VERSION = "([^"]+)"', read("ai_council_web.py"), re.M).group(1)
ui = re.search(r"UI_VERSION = '([^']+)'", read("web/index.html")).group(1)
readme, log = read("README.md"), read("CHANGELOG.md")
first = re.search(r"^## (V[\d.]+)", log, re.M).group(1)
checks = [
    (ui == version, f"UI_VERSION({ui}) == VERSION({version})"),
    (f"**현재 버전: V{version}**" in readme, f"README 맨 위 '현재 버전: V{version}'"),
    (f"**Current version: V{version}**" in readme, f"README English 'Current version: V{version}'"),
    (f"[V{version}](CHANGELOG.md#" in readme, f"README 최근 업데이트 표에 V{version}"),
    (first == f"V{version}", f"CHANGELOG 첫 버전 항목({first}) == V{version}"),
    (f"| [V{version}](#" in log, f"CHANGELOG 버전 한눈에 보기 표에 V{version}"),
    (read("CLAUDE.md") == read("AGENTS.md"), "CLAUDE.md == AGENTS.md"),
]
for ok, msg in checks:
    print(("PASS " if ok else "FAIL ") + msg)
if not all(ok for ok, _ in checks):
    sys.exit(1)
print("ALL PASS")
