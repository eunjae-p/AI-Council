# AI Council V0.8.0

하나의 채팅 화면에서 질문마다 **GPT / Claude / 둘 다 + 최종 결론**을 골라 답을 받는 로컬 멀티모델 채팅 앱입니다.
백엔드는 각 PC에서 구독 계정으로 로그인한 **Codex CLI**와 **Claude Code CLI**이며, OpenAI·Anthropic API 키는 사용하지 않습니다. CLI 호출이 실패해도 다른 API로 우회하지 않습니다.

## 처음 설치하기 (팀원용)

각자 자기 PC에서, 자기 구독 계정으로 실행합니다. 대화 기록은 각자 PC의 `data/`에만 저장되고 공유되지 않습니다.
필요한 것: ChatGPT 구독(GPT 사용) 그리고/또는 Claude Pro·Max 등 구독(Claude 사용), 인터넷 연결.

1. 저장소를 받습니다. (Git이 없으면 GitHub 페이지의 **Code → Download ZIP** 후 압축 해제)
   ```powershell
   git clone https://github.com/eunjae-p/AI-Council.git
   ```
2. 받은 폴더의 **`Setup.cmd`를 더블클릭**합니다. 자동으로:
   - Python, Node.js, Git이 없으면 winget으로 설치
   - Codex CLI 설치·업데이트, Claude Code 설치 (공식 설치 프로그램, 이후 자동 업데이트)
   - 로그인이 안 되어 있으면 로그인 창을 띄움 (브라우저에서 **자기 계정**으로 로그인)
   - 바탕화면에 **AI Council** 바로가기 생성
3. 바탕화면의 **AI Council**을 실행합니다. 왼쪽 아래에 Codex·Claude 버전이 보이고 빨간 "로그인 필요"가 없으면 준비 완료입니다.

설치가 중간에 실패하면 마지막 표에 실패 항목과 해결 방법이 나옵니다. 새로 설치한 프로그램이 인식되지 않으면 창을 닫고 `Setup.cmd`를 한 번 더 실행하세요. 관리자 권한은 필요 없지만, 회사 PC에서 설치가 막혀 있으면 IT 담당자에게 문의하세요.

## GPT·Claude 로그인 (PC마다 처음 한 번)

AI Council에는 별도 로그인 화면이 없습니다. **그 PC에 설치된 Codex CLI와 Claude Code CLI에 한 번 로그인**해 두면, Council이 그 로그인 정보로 GPT와 Claude를 호출합니다. 사용량은 각자 자기 구독에서 차감됩니다.

**방법 1 — `Setup.cmd` (권장)**
`Setup.cmd`를 실행하면 마지막 단계에서 로그인 상태를 확인하고, 로그인이 필요하면 `지금 로그인할까요? (Y/n)`를 묻습니다. Enter를 누르면 브라우저가 열리니 각 계정으로 로그인하세요.

**방법 2 — 터미널에서 직접**
PowerShell 또는 명령 프롬프트에서 실행합니다.

| 대상 | 명령 | 브라우저에서 로그인할 계정 |
|---|---|---|
| GPT | `codex login` | ChatGPT 계정 (Plus/Pro 등 구독) |
| Claude | `claude auth login` | Claude 계정 (Pro/Max 등 구독, 무료 플랜은 불가) |

로그인 확인: `codex login status`, `claude auth status`

**로그인 후** Council 왼쪽 아래 **버전 다시 확인**을 누르면 빨간 "로그인 필요" 표시가 사라집니다. 이 표시를 누르면 해당 로그인 명령이 복사됩니다.

**문제가 생기면**
- `codex` / `claude` 명령을 찾을 수 없음 → CLI가 설치되지 않았거나 PATH에 없음. `Setup.cmd`를 다시 실행하고, 그래도 안 되면 터미널 창을 새로 열어 다시 시도하세요.
- 브라우저 로그인 페이지가 열리지 않거나 멈춤 → 회사 네트워크(방화벽·폐쇄망)가 OpenAI/Anthropic 로그인 주소를 막고 있을 수 있습니다. 인터넷이 되는 환경에서 사용하세요.
- 한쪽 구독만 있는 경우 → 그 모델만 사용할 수 있습니다. 답변 대상을 GPT 또는 Claude 하나로 선택하세요.
- GPT 모델 오류(`not supported when using Codex with a ChatGPT account`) → Council의 "모델 설정"에서 GPT를 **계정 기본값**으로 두세요.

## 업데이트

Council 왼쪽 아래 **업데이트 확인 → 지금 업데이트**를 누르면 GitHub 최신 버전을 받아 자동으로 다시 시작합니다(대화 기록은 유지). Git으로 받은(`git clone`) 폴더에서만 동작하므로 ZIP 대신 `git clone`을 권장합니다. 처음에는 모델을 **계정 기본값**으로 쓰는 것을 권장합니다.

## 실행

`AI-Council_Web.cmd`를 더블클릭하면 로컬 서버가 시작되고 브라우저에서 `http://127.0.0.1:8765`가 열립니다. 이 PC에서만 접속할 수 있습니다. 종료는 화면 왼쪽 아래 **앱 종료** 또는 콘솔 창에서 `Ctrl+C`.

요구 사항

- Python 3.10 이상 (표준 라이브러리만 사용, 추가 패키지 없음)
- 구독 계정으로 로그인된 `codex` CLI, `claude` CLI (PATH에서 찾을 수 있어야 함)

## 주요 기능

- **대화 모드 / 작업 모드** (기본값: 대화 모드, 앱을 열 때마다 대화 모드로 시작)
  - 대화 모드: CLI를 빈 임시 폴더에서 도구 없이 실행합니다. Claude는 `--disallowedTools "*"`와 채팅용 시스템 프롬프트를, Codex는 읽기 전용 샌드박스를 씁니다. 프로젝트 파일에 접근하지 않습니다.
  - 작업 모드: 입력한 작업 폴더에서 실행하며 파일 읽기만 허용합니다(Claude는 `Read, Glob, Grep` 도구만). 파일을 수정하지 않습니다.
  - 설치된 CLI 버전이 옵션을 모르면 기본 옵션으로 한 번 다시 시도합니다.
- **파일 첨부 / 워크플로우 분석**: 입력창의 📎 버튼이나 끌어다 놓기로 JSON·텍스트 파일을 최대 5개(각 2MB) 첨부합니다. GPT와 Claude에 같은 내용이 전달됩니다.
  - ComfyUI 워크플로우 JSON(UI·API 형식)은 코드가 먼저 요약합니다: 노드 상태, **색상 등급**(빨강=MUST, 노랑·주황=SHOULD, 판정 제외: MarkdownNote·Note·Label (rgthree)·SetNode·GetNode), 모델 파일, 노드 팩(cnr_id/aux_id), 그룹, 서브그래프.
  - 모델은 이 요약과 원본(길면 앞부분)을 함께 받아 분석하므로 노드를 빠뜨리거나 지어내는 일이 줄어듭니다.
  - 요약은 대화 기록에 남아 다음 질문에서 "아까 그 워크플로우"로 이어서 물어볼 수 있습니다. 원본은 `data/attachments/`에 보관됩니다(Git 제외).
  - 첨부가 있거나 작업 모드일 때는 모델별 제한 시간이 300초로 늘어납니다.
- **답변 대상 선택**: GPT / Claude / 둘 다 + 최종 결론. 모델은 "모델 설정"에서 고르거나 직접 입력하며, `계정 기본값`은 각 CLI의 기본 설정을 그대로 씁니다.
- **공용 대화 기록**: 어떤 모델이 답하든 같은 대화 기록을 읽습니다. 프롬프트에는 `[사용자] [GPT] [Claude] [Council 최종 결론]` 화자 표시가 붙어 서로의 답변을 혼동하지 않게 합니다.
- **장기 대화 자동 요약**: 원문은 전부 보존하고, 모델에는 `누적 장기 요약 + 최근 대화 원문(메시지 단위) + 현재 질문`을 보냅니다.
  - 요약되지 않은 원문이 약 30,000자를 넘을 때만 요약을 갱신하고, 최근 약 12,000자는 원문으로 남깁니다.
  - 요약은 사용자 선호, 중요한 사실, 결정 사항, 미해결 항목, 대화 흐름을 보존하도록 지시합니다.
  - 요약한 모델과 시각을 기록하고, 화면 상단에서 요약 내용을 펼쳐 볼 수 있습니다.
  - 요약이 실패해도 원문은 그대로이며 채팅은 계속됩니다. 실패 내용은 화면에 표시됩니다.
- **대화 관리**: 첫 질문으로 제목 자동 생성, 제목 변경, 보관/보관 해제, 휴지통 삭제·복구·영구 삭제, 최근 수정 순 정렬.
- **전체 검색**: 모든 대화(보관 포함)의 제목과 메시지 내용을 검색하고, 결과를 누르면 해당 메시지로 이동합니다.
- **Markdown 내보내기**: 현재 대화를 `exports/` 폴더에 저장하고 브라우저로도 내려받습니다. 같은 이름이 있으면 `_2`, `_3`이 붙습니다.
- 새로고침해도 현재 대화가 유지됩니다(주소의 `#c=<대화 ID>`).
- 답변 생성 중에는 보내기 버튼이 **■ 중지**로 바뀝니다. 누르거나 `Esc`를 누르면 즉시 멈추고, 이미 완료된 모델의 답변은 남습니다.
- 같은 대화에 두 질문을 동시에 보내거나, 답변 생성 중인 대화를 삭제할 수 없습니다. 브라우저를 닫아도 진행 중인 답변은 끝까지 저장됩니다.

## CLI 버전 확인

왼쪽 아래에 Codex·Claude CLI의 설치 버전이 표시됩니다. Codex는 자동 업데이트되지 않으므로 새 버전이 있으면 노란 안내가 나오고, 누르면 업데이트 명령(`npm i -g @openai/codex@latest`)이 복사됩니다. 터미널에서 실행한 뒤 AI Council을 다시 시작하세요. Claude Code는 기본적으로 스스로 업데이트됩니다.

## 저장 구조

| 경로 | 내용 |
|---|---|
| `data/conversations/<id>.jsonl` | 대화 원문 (추가만 함) |
| `data/conversations/<id>.meta.json` | 제목, 생성·수정 시각, 보관 여부, 장기 요약(`summary`, `summarized_through`, `summary_model`) |
| `data/trash/` | 삭제한 대화 (복구 가능) |
| `data/attachments/<id>/` | 첨부 원본 (영구 삭제 시 함께 삭제) |
| `data/backups/` | "대화 기록 지우기" API 사용 시 남기는 백업 |
| `exports/` | Markdown 내보내기 결과 |

`data/`와 `exports/`는 개인 대화가 들어 있으므로 Git에 올라가지 않습니다(`.gitignore`). V0.5에서 만든 대화 파일은 그대로 읽히며, 처음 열 때 `meta.json`만 새로 생깁니다.

## 파일 구성

| 파일 | 역할 |
|---|---|
| `ai_council_web.py` | 로컬 웹 서버와 API (주력) |
| `council_core.py` | CLI 탐색·호출, 타임아웃·오류 처리 공용 코드 |
| `council_store.py` | 대화 저장, 검색, 휴지통, Markdown 내보내기 (나중에 SQLite FTS로 교체 가능하도록 분리) |
| `council_workflow.py` | ComfyUI 워크플로우 JSON 요약 (노드·색상 등급·모델·노드 팩·서브그래프) |
| `council_attach.py` | 첨부 파일 검사·보관·프롬프트 구성 |
| `council_update.py` | Council 자체 업데이트 (GitHub → 이 PC, 안전 검사, 자동 재시작) |
| `council_versions.py` | 설치된 CLI 버전과 npm 최신 버전 비교 (업데이트는 하지 않고 안내만) |
| `council_context.py` | 모델에 넘길 컨텍스트 구성과 장기 요약 |
| `web/index.html` | 채팅 UI (HTML/CSS/JavaScript, 외부 라이브러리 없음) |
| `AI-Council_Web.cmd` | 실행 파일 |
| `CLAUDE.md`, `AGENTS.md` | 수정 작업 규칙 (Claude Code·Codex 공용) |
| `tests/` | 가짜 CLI로 하는 테스트 (`python tests/test_api.py`, `python tests/test_update.py`) |
| `Setup.cmd`, `setup.ps1` | 처음 설치 도우미 (Python·Node.js·Git·Codex CLI·Claude Code 설치, 로그인 안내, 바로가기) |
| `AI-Council_CLI.ps1` | CLI 연결 확인·디버깅용 PowerShell 스크립트 |

## CLI 연결 확인 (디버깅)

```powershell
.\AI-Council_CLI.ps1 "양자 컴퓨팅을 한 문단으로 설명해줘"
.\AI-Council_CLI.ps1 "질문" -TimeoutSeconds 300
.\AI-Council_CLI.ps1 "질문" -GptModel "gpt-6.1-sol" -ClaudeModel "sonnet"
```

질문을 생략하면 반복 입력 모드가 시작됩니다. 빈 줄이나 `/exit`로 종료합니다. 이 스크립트는 V0.4 방식의 4단계 자동 토론(초안 → 상호 검토 → 최종)을 실행하며 대화 기록은 저장하지 않습니다.

## 참고

- CLI별 제한 시간은 180초입니다(`council_core.py`의 `TIMEOUT_SECONDS`).
- `둘 다 + 최종 결론`은 GPT 답변, Claude 답변, Claude의 결론 정리까지 CLI를 3번 호출합니다. 한 모델이 실패하면 나머지 모델의 답변만 표시하고 결론 정리는 건너뜁니다.
- 이 앱은 PC가 켜져 있고 서버가 실행 중일 때만 동작합니다.
