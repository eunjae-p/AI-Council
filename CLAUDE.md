# AI Council 작업 규칙 (Claude Code · Codex 공용)

이 파일은 어느 PC, 어느 에이전트(Claude Code / Codex)가 이 저장소를 수정하든 따라야 하는 규칙입니다.
`CLAUDE.md`와 `AGENTS.md`는 같은 내용이며, 한쪽을 고치면 다른 쪽도 똑같이 고칩니다.

## 프로젝트 개요
- Codex CLI(GPT)와 Claude Code CLI(Claude)를 구독 계정으로 호출하는 **로컬 멀티모델 채팅 앱**입니다.
- OpenAI/Anthropic **API 키를 쓰지 않습니다.** CLI가 실패해도 API로 우회하지 않습니다.
- Python **표준 라이브러리만** 사용합니다. 프런트엔드는 `web/index.html` 한 파일(HTML/CSS/JS), npm·프레임워크 추가 금지.
- 사용자 화면 문구는 한국어로 씁니다.

## 버전 관리 = GitHub이 기준 (클라우드 개념)
- 기준 저장소: `https://github.com/eunjae-p/AI-Council` 의 `main` 브랜치.
- **모든 수정은 GitHub에 올려야 끝난 것**으로 봅니다. 각 PC(집, 회사, 팀원)는 GitHub에서 받아 갑니다.
  - 받는 방법: Council 왼쪽 아래 **업데이트 확인 → 지금 업데이트** (또는 `git pull`).
- 작업 시작 전: `git pull` 로 최신 상태에서 시작합니다.
- 한 번에 **한 에이전트만** 파일을 수정합니다. 다른 에이전트는 검토만 합니다.

## 수정할 때마다 지키는 순서
1. 코드 수정
2. 버전 올리기 — `ai_council_web.py` 의 `VERSION` 과 `web/index.html` 의 `UI_VERSION` 을 **항상 같은 값으로** 함께 올립니다.
   (값이 다르면 화면에 "서버를 재시작하세요" 경고가 뜹니다. 업데이트 기능도 이 값으로 새 버전을 판단합니다.)
3. `CHANGELOG.md` 맨 위에 변경 내역 추가, 필요하면 `README.md` 갱신
4. 테스트 (실제 GPT/Claude를 호출하지 않음)
   ```
   python tests/test_api.py
   python tests/test_update.py
   ```
5. 커밋하고 `main` 에 push
6. 작업한 PC가 Council을 실행 중이면 재시작(또는 업데이트 버튼)으로 반영 확인

## PC 폴더를 원격으로 수정하는 경우 (클라우드 세션 → PC 파일 전송)
- 쓰기 전에 PC 파일의 수정 시각이 마지막으로 확인한 값과 같은지 확인하고, 다르면 덮어쓰지 않고 먼저 알립니다.
- 전송할 임시 파일은 **매번 새 이름/새 폴더**로 만듭니다. (같은 경로를 재사용하면 이전 내용이 다시 전송된 사례가 있음)
- 쓴 뒤에는 PC 파일을 다시 읽어 내용이 같은지 대조합니다.
- PC 폴더의 Git 기록은 Council 업데이트 버튼이 맞춰 줍니다(내용이 같으면 기록만 정리).

## 금지 / 주의
- `data/`(대화 기록·첨부 원본), `exports/` 는 절대 커밋하지 않습니다 (`.gitignore` 유지).
- `git reset --hard`, 사용자 파일에 대한 `git checkout --` 등 되돌릴 수 없는 명령은 사용자 확인 없이 쓰지 않습니다.
- 대화 원문 JSONL을 다시 쓰는 마이그레이션 금지 (추가만 함).
- `.cmd` / `.ps1` 은 CRLF 유지 (`.gitattributes`), `setup.ps1` 은 UTF-8 BOM 유지 (Windows PowerShell 5.1 한글).

## 파일 구성
| 파일 | 역할 |
|---|---|
| `ai_council_web.py` | 로컬 웹 서버(127.0.0.1:8765)와 API, `VERSION` |
| `web/index.html` | 채팅 UI, `UI_VERSION` |
| `council_core.py` | CLI 호출·타임아웃·중지(CancelToken)·오류 안내, 대화/작업 모드 |
| `council_context.py` | 메시지 단위 맥락 구성, 장기 요약 |
| `council_store.py` | 대화 저장·메타·휴지통·검색·Markdown 내보내기 |
| `council_attach.py` | 첨부 파일 검사·보관·프롬프트 구성 |
| `council_workflow.py` | ComfyUI 워크플로우 JSON 요약 (색상 등급 규칙 포함) |
| `council_versions.py` | Codex/Claude CLI 버전·로그인 상태 |
| `council_update.py` | Council 자체 업데이트 (GitHub → PC, 안전 검사, 재시작) |
| `Setup.cmd`, `setup.ps1` | 처음 설치 도우미 |
| `tests/` | 가짜 CLI(`fake_bin`)를 쓰는 테스트 |

## 팀 워크플로우 규칙 (워크플로우 파서 관련)
- 노드 색상 등급: 빨강 = MUST(필수 입력·웹UI 노출), 노랑·주황 = SHOULD(선택 노출), 그 외 = 일반.
- 색상 판정 제외: MarkdownNote, Note, Label (rgthree), SetNode, GetNode (SetNode/GetNode 는 연결 타입에 따라 색이 자동 지정됨).
