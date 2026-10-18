# AI Council

**🇰🇷 한국어** · [🇺🇸 English](#english)

> **현재 버전: V0.16.0** (2026-10-19) · [전체 업데이트 내역 보기 → CHANGELOG.md](CHANGELOG.md)

하나의 채팅 화면에서 질문마다 **GPT / Claude / 토론(Discussion)** 을 골라 답을 받는 로컬 멀티모델 채팅 앱입니다.
각 PC에서 **구독 계정으로 로그인한 Codex CLI(GPT)와 Claude Code CLI(Claude)** 를 사용하며, API 키는 쓰지 않습니다.

## 🆕 최근 업데이트

| 버전 | 날짜 | 주요 변경 |
|---|---|---|
| [V0.16.0](CHANGELOG.md#v0160-2026-10-19) | 10-19 | **🛠 작업 모드 = Claude Code처럼** — 파일 만들기·고치기·명령 실행(허용 목록 + 승인), 수정 모드는 작업 모드로 통합 |
| [V0.15.0](CHANGELOG.md#v0150-2026-10-18) | 10-18 | **🌐 한국어 / English** — 화면·서버 안내·설치 스크립트 영어 지원, 왼쪽 위 언어 전환 |
| [V0.14.1](CHANGELOG.md#v0141-2026-10-17) | 10-17 | **🇺🇸 영어 설명 추가** — README 아래에 English 안내 (화면 문구는 한국어 그대로) |
| [V0.14.0](CHANGELOG.md#v0140-2026-10-15) | 10-15 | **✏️ 수정 모드** — GPT·Claude가 작업 폴더 파일을 직접 만들고 고침 (저장점·변경 확인·확정/되돌리기) |
| [V0.13.2](CHANGELOG.md#v0132-2026-10-12) | 10-12 | Council 버전도 새 버전이 있을 때만 노란 업데이트 표시 |

이전 버전은 [CHANGELOG.md](CHANGELOG.md)에서 볼 수 있습니다.

## 목차

1. [무엇을 할 수 있나요](#-무엇을-할-수-있나요)
2. [처음 설치하기](#-처음-설치하기-팀원용) (Windows · [Mac](#-mac에서-설치하기))
3. [GPT·Claude 로그인](#-gptclaude-로그인-pc마다-처음-한-번)
4. [실행 · 종료](#-실행--종료)
5. [Council 업데이트](#-council-업데이트)
6. [사용법](#-사용법)
7. [문제 해결](#-문제-해결)
8. [저장 위치 · 보안](#-저장-위치--보안)
9. [개발자용](#-개발자용)

---

## 💡 무엇을 할 수 있나요

| 답변 대상 | 언제 쓰나요 | 모델 호출 |
|---|---|---|
| **GPT** | 빠른 질문, 프롬프트 작성 | 1번 |
| **Claude** | 빠른 질문, 워크플로우 분석 | 1번 |
| **토론 (Discussion)** ⚠ | 설계 검토·의사결정처럼 정답이 하나가 아닌 주제 | 5번 (사용량 약 5배) |

- **ComfyUI 워크플로우 JSON 분석** — 노드·색상 등급(MUST/SHOULD)·모델 파일을 코드가 먼저 정리해 정확하게 분석
- **이미지·영상 분석** — 끌어다 놓기·Ctrl+V 붙여넣기, 영상은 프레임 12장으로 분석
- **🛠 작업 모드** — Claude Code·Codex처럼 작업 폴더에서 폴더·파일 만들기, 코드 작성, 명령 실행(설치·서버 실행 등). 명령은 허용 목록 + 승인
- **🌐 웹 검색** — 최신 정보·공식 문서 확인이 필요할 때 켜기
- **🔌 MCP** — Claude에 연결된 도구(Higgsfield·Notion 등) 사용, 허용한 도구만 실행
- **🌐 한국어 / English** — 왼쪽 위 `EN` / `한국어` 버튼으로 화면 언어 전환 (처음에는 브라우저 언어를 따름)
- **대화 관리** — 자동 제목, 보관·휴지통, 전체 검색, 긴 대화 자동 요약
- **Markdown 내려받기** — 답변마다 **⤓ MD**(그 답변만), 오른쪽 위 **Chat_md**(대화 전체)

## 📦 처음 설치하기 (팀원용)

각자 자기 PC에서, 자기 구독 계정으로 씁니다. 대화 기록은 각자 PC에만 저장되고 공유되지 않습니다.
필요한 것: ChatGPT 구독(GPT) 그리고/또는 Claude Pro·Max 구독(Claude), 인터넷 연결.

1. 원하는 폴더에서 저장소를 받습니다. **ZIP이 아니라 `git clone`** 으로 받아야 자동 업데이트가 됩니다.
   ```powershell
   git clone https://github.com/eunjae-p/AI-Council.git
   ```
2. 받은 폴더의 **`Setup.cmd`** 를 더블클릭합니다. 자동으로:
   - Python, Node.js, Git, ffmpeg 설치 (없을 때만)
   - Codex CLI, Claude Code 설치
   - 로그인 안내 (브라우저에서 **자기 계정**으로 로그인)
   - 바탕화면에 **AI Council** 바로가기 생성
3. 바탕화면의 **AI Council** 을 실행합니다. 왼쪽 아래에 빨간 "로그인 필요"가 없으면 준비 완료입니다.

설치가 중간에 실패하면 마지막 표에 실패 항목과 해결 방법이 나옵니다. 새로 설치한 프로그램이 인식되지 않으면 `Setup.cmd` 를 한 번 더 실행하세요.

### 🍎 Mac에서 설치하기

1. **터미널**(응용 프로그램 → 유틸리티)을 열고 원하는 폴더에서 받습니다.
   ```bash
   git clone https://github.com/eunjae-p/AI-Council.git
   ```
   `git` 이 없다는 창이 뜨면 **설치**를 누르고(Xcode 명령줄 도구), 끝나면 같은 명령을 다시 실행하세요.
2. Finder에서 받은 폴더의 **`Setup-mac.command`** 를 더블클릭합니다. 자동으로:
   - Homebrew(Mac 프로그램 설치 도구)가 없으면 공식 설치 프로그램 실행 — Mac 로그인 비밀번호를 물을 수 있습니다
   - Python 3.10 이상, Node.js, ffmpeg, Codex CLI, Claude Code 설치
   - 로그인 안내, 바탕화면에 **AI Council** 실행 아이콘 생성
   - "확인되지 않은 개발자" 경고로 열리지 않으면: 파일을 **우클릭 → 열기** 한 번
3. 바탕화면의 **AI Council** 을 더블클릭하면 서버가 백그라운드로 켜지고 브라우저가 열립니다. (뜨는 터미널 창은 닫아도 됩니다)

- 업데이트: 화면의 **업데이트 확인 → 지금 업데이트**, 또는 **`Update-mac.command`** 더블클릭
- 종료: 화면 왼쪽 아래 **앱 종료**. 기록은 `data/logs/server.log`

## 🔑 GPT·Claude 로그인 (PC마다 처음 한 번)

Council에는 별도 로그인 화면이 없습니다. 그 PC의 Codex CLI와 Claude Code에 한 번 로그인해 두면, 사용량은 각자 자기 구독에서 차감됩니다.

- **가장 쉬운 방법**: Council 왼쪽 아래 빨간 **"로그인 필요 · 로그인하기"** 클릭 → 브라우저에서 로그인 → 자동 확인
- `Setup.cmd` 를 실행해도 마지막 단계에서 로그인을 안내합니다.
- 터미널에서 직접 하려면:

| 대상 | 명령 | 로그인할 계정 |
|---|---|---|
| GPT | `codex.cmd login` | ChatGPT 계정 (Plus/Pro 등) |
| Claude | `claude auth login` | Claude 계정 (Pro/Max 등, 무료 플랜 불가) |

로그인 확인: `codex.cmd login status`, `claude auth status` → 그 뒤 Council 왼쪽 아래 **버전 다시 확인**.

## ▶ 실행 · 종료

- **실행**: 바탕화면 **AI Council** (또는 `AI-Council_Web.cmd`). 창 없이 백그라운드로 켜지고 브라우저에서 `http://127.0.0.1:8765` 가 열립니다. 이 PC에서만 접속됩니다.
- **종료**: 화면 왼쪽 아래 **앱 종료**. 브라우저 탭만 닫으면 서버는 계속 켜져 있고, 바로가기를 다시 누르면 화면만 다시 열립니다.
- **문제 확인용 실행**: `AI-Council_Debug.cmd` (콘솔 창에 서버 메시지 표시). 백그라운드 기록은 `data/logs/server.log`.

## 🔄 Council 업데이트

GitHub의 최신 버전을 받는 방법은 두 가지입니다. 대화 기록은 그대로 유지됩니다.

1. **화면에서**: 새 버전이 있으면 왼쪽 아래 Council 버전 아래에 노란 **⬆ 업데이트하기** → **지금 업데이트** (자동 재시작·새로고침)
2. **화면 없이**: 폴더의 **`Update.cmd`** 더블클릭 → `Y`

- 이 PC에서 직접 고친 파일이 있으면 덮어쓰지 않고 멈춥니다.
- **GPT·Claude 프로그램(CLI) 업데이트**는 별개입니다. 새 버전이 있으면 왼쪽 아래 노란 **"⬆ 업데이트하기"** 를 누르면 자동으로 설치됩니다 (1~2분, Council 재시작 불필요).
- `Setup.cmd` 는 처음 설치용이며 Council 코드는 업데이트하지 않습니다.

## 🧭 사용법

### 💬 대화 / 🛠 작업 모드
| 모드 | 할 수 있는 일 | 언제 |
|---|---|---|
| 💬 **대화** (기본) | 질문에 답만 (파일·명령 접근 없음) | 일반 질문, 프롬프트 작성 |
| 🛠 **작업** | 작업 폴더에서 **읽기·만들기·고치기 + 명령 실행** | 폴더·코드·서버 만들기, 버그 수정, 설치, 블렌더 작업(🔌 MCP와 함께) |

**🛠 작업 모드 사용법**
1. 입력창 위 **🛠 작업** → 작업 폴더 경로 입력 (예: `D:\my-project`) → 할 일을 적고 보내기.
2. **명령 실행은 허용 목록 + 승인**: `mkdir`, `ls`, `git status` 같은 명령은 바로 실행됩니다.
   목록에 없는 명령(예: `npm install`, `python app.py`)은 실행하지 않고 답변 아래에 **🛡 승인 카드**가 뜹니다 →
   **이번만 허용하고 다시 실행 / 항상 허용하고 다시 실행 / 허용 안 함**. 다시 실행하면 이미 만든 파일에서 이어서 작업합니다.
3. 허용 목록 관리: 작업 폴더 옆 **🛡** 버튼 (추가·삭제·기본값으로). `python`·`node`·`rm`·`curl` 처럼 사실상 무엇이든 할 수 있는 명령은 빨간 표시가 붙습니다.
4. **저장점(선택)**: 작업 폴더가 Git 저장소면 끝난 뒤 **📝 변경된 파일** 카드 → **✅ 확정 (커밋)** / **↩ 되돌리기**.
   저장 안 된 변경이 있으면 시작 전에 "저장점 만들고 시작 / 저장점 없이 진행"을 고릅니다. Git 저장소가 아닌 폴더(예: `D:\` 아래 새 폴더)는 그냥 진행합니다.

- **GPT(Codex)**: `workspace-write` 샌드박스 — 작업 폴더 안에서만 쓰고 명령도 실행하지만 **인터넷은 막혀** `npm install` 같은 설치는 실패할 수 있습니다. 설치가 필요한 작업은 Claude를 쓰세요.
- **블렌더 등 연결된 도구**: 모드와 별개로 **🔌 MCP 켬** (Claude Code에 Blender MCP가 등록돼 있어야 함).
- **토론 + 작업**: GPT·Claude가 **읽기만 하며** 계획을 토론하고, 결론이 나면 **Claude 한 명만** 결론대로 작업합니다.
- **서버 실행**: 오래 켜 두는 서버는 백그라운드로 실행하도록 지시합니다. 끄는 방법은 답변에 안내됩니다.
- ⚠ **운영 중인 서비스 폴더는 복사본에서** 작업하고 확인 후 반영하는 것을 권장합니다. 모든 명령을 묻지 않고 실행하는 모드는 쓰지 않습니다.

### 토론 (Discussion) ⚠
1. **1라운드 독립 의견** — GPT·Claude가 서로의 답을 보지 않고 동시에 답합니다.
2. **2라운드 교차 검토** — 각자 상대 답을 읽고 동의·반박·누락·입장 변화를 씁니다.
3. **최종 결론** — **결론 / 합의된 점 / 의견이 갈린 점 / 확인이 필요한 항목** 으로 정리합니다.

- **행동 지침**: 근거로만 판단하고(새 근거 없이 양보·반대 금지), 확신도를 밝히고, 둘 다 검증하지 않은 공통 가정을 따로 표시합니다.
- **중립 정리**: 결론을 정리하는 Claude는 두 답변을 이름을 가린 채(모델 A/B, 무작위) 받아 자기 답을 편들지 못합니다.
- 화면에는 결론이 먼저, **토론 과정 보기** 를 펼치면 라운드별 답변이 보입니다. **📁 토론 기록 폴더 열기** 로 PC에 저장된 기록을 엽니다.
- **읽는 법**: 두 모델이 합의했다고 정답은 아닙니다. **"의견이 갈린 점"과 "확인이 필요한 항목"** 을 먼저 확인하세요.
- 사용량이 단독의 약 5배입니다. 간단한 질문·워크플로우 분석·프롬프트 작성은 단독 모델이 효율적입니다.

### 🌐 웹 검색
- 입력창 위 **웹 검색 켬/끔**. 켜면 GPT(Codex `--search`)·Claude(WebSearch·WebFetch)가 웹을 검색하고 출처를 밝힙니다.
- 가격·API·약관처럼 바뀔 수 있는 정보에 켜세요. 답변 시간과 사용량이 늘어납니다.

### 🔌 MCP (연결된 도구)
- 입력창 위 **🔌 MCP 켬/끔** (기본 꺼짐). 켜면 Claude 계정(claude.ai 커넥터)·Claude Code에 연결된 도구(예: Higgsfield, Notion)를 Claude가 쓸 수 있습니다.
- **⚙ (MCP 도구 관리)** → **도구 목록 가져오기** → 바로 실행해도 되는 도구에 **"항상 허용"** 체크. 조회 도구(잔액·내역 조회 등)만 허용해 두는 것을 권장합니다.
- 허용하지 않은 도구를 Claude가 쓰려 하면 **실행하지 않고** 답변 아래에 도구·입력 내용을 보여 줍니다 → **이번만 허용 / 항상 허용 / 허용 안 함**.
- ⚠ 생성·수정·결제처럼 크레딧이 들 수 있는 도구는 빨간 **실행·비용 가능** 표시가 붙습니다. 입력 내용을 확인하고 허용하세요.
- GPT(Codex)의 MCP는 아직 지원하지 않습니다.

### 첨부 (📎 · 끌어다 놓기 · Ctrl+V)
| 종류 | 형식 · 크기 | 처리 |
|---|---|---|
| 텍스트·JSON | json, txt, md, py 등 · 2MB, 최대 5개 | ComfyUI 워크플로우는 코드가 노드·**색상 등급**·모델·노드 팩·서브그래프를 먼저 요약 |
| 이미지 | png, jpg, webp, gif, bmp · 20MB | 모델이 직접 봅니다 |
| 영상 | mp4, mov, mkv, webm 등 · 2GB | ffmpeg로 프레임 12장 + 길이·해상도·fps 정보 (소리는 분석 안 함) |

워크플로우 색상 등급: 빨강 = MUST, 노랑·주황 = SHOULD (판정 제외: MarkdownNote, Note, Label (rgthree), SetNode, GetNode).

### 화면 안내
- **화면 언어**: 왼쪽 위 `EN` / `한국어` 버튼. 처음에는 브라우저 언어를 따릅니다(한국어가 아니면 영어). 대화 기록 원문은 바뀌지 않고, Council 안내·오류 문구만 바뀝니다. 설치·업데이트 창은 Windows/Mac 언어를 따릅니다.
- **화면 테마**: 왼쪽 위 `AI Council` 옆 🌙/☀️/🖥️ 버튼으로 다크·라이트·시스템 설정 따르기를 바꿉니다.
- **모델 표시**: 계정 기본값을 써도 실제 모델 이름이 보입니다 (예: `GPT-6.1 Sol (계정 기본)`).
- **왼쪽 아래**: CLI 버전·업데이트·로그인 상태, 오늘 사용 횟수, **남은 사용량 보기** (공식 사용량 페이지).
- **대화 목록 아이콘**: 💬 대화 모드 · 🔧 작업 모드 · `GPT`/`Claude` 배지 = 그 대화에서 답한 모델.
- **■ 중지**: 답변 생성을 즉시 멈춥니다. `Esc`는 한 번 더 확인합니다(창이 열려 있으면 창만 닫음). 완료된 답변은 남고, 중지 기록에 시점·경과 시간이 남습니다.

## 🛠 문제 해결

| 증상 | 해결 |
|---|---|
| PowerShell에서 `codex login` → "스크립트를 실행할 수 없으므로 codex.ps1…" | **`codex.cmd login`** 으로 입력 (Windows 실행 정책 문제). 또는 Council의 "로그인하기" 버튼 사용 |
| `codex` / `claude` 명령을 찾을 수 없음 | `Setup.cmd` 실행 후 터미널 창을 새로 열기 |
| 브라우저 로그인 페이지가 안 열림 | 회사 네트워크가 로그인 주소를 막았을 수 있음 → 인터넷이 되는 환경에서 로그인 |
| 화면 위에 "서버가 화면보다 오래된 버전" | 바탕화면 AI Council 다시 실행. 그래도 그대로면 작업 관리자 → 세부 정보에서 `pythonw.exe` 를 모두 끝낸 뒤 실행 |
| "Git으로 설치되지 않은 폴더" | ZIP으로 받은 폴더입니다. `git clone` 으로 다시 받기 |
| 영상 첨부가 안 됨 ("ffmpeg 없음") | `Setup.cmd` 실행 (또는 `winget install Gyan.FFmpeg`) 후 Council 재시작 |
| GPT 모델 오류 (`not supported … ChatGPT account`) | 모델 설정에서 GPT를 **계정 기본값** 으로 |
| 한쪽 구독만 있음 | 그 모델만 선택해서 사용 (토론은 두 구독이 모두 필요) |

## 🔒 저장 위치 · 보안

| 경로 | 내용 |
|---|---|
| `data/conversations/` | 대화 원문(`.jsonl`, 추가만 함)과 제목·요약 등 메타 정보 |
| `data/attachments/` | 첨부 원본 |
| `data/debates/` | 토론 기록 (`질문.md`, `1_GPT.md`, `1_Claude.md`, `2_*_검토.md`, `결론.md`) |
| `data/trash/` | 삭제한 대화 (복구 가능, 영구 삭제 시 첨부·토론 기록도 삭제) |
| `data/cli_state.json` | 사용 횟수, 계정 기본 모델 이름 |
| `data/mcp_settings.json`, `data/mcp_state.json` | MCP "항상 허용" 도구, 마지막으로 확인한 도구 목록 |
| `exports/` | Markdown 내보내기 |

- `data/` 와 `exports/` 는 **GitHub에 올라가지 않습니다** (`.gitignore`).
- ⚠ CLI를 쓰더라도 모델은 클라우드에서 돌아갑니다. 질문·첨부는 **OpenAI·Anthropic 서버로 전송**되므로 반출이 제한된 자료는 회사 규정을 확인하세요.

## 💻 개발자용

- 수정 규칙: [`CLAUDE.md`](CLAUDE.md) (= `AGENTS.md`, Claude Code·Codex 공용). 수정하면 버전 올리기 → CHANGELOG·README 갱신 → 테스트 → GitHub push.
- 요구 사항: Python 3.10 이상 (표준 라이브러리만), 프런트엔드는 `web/index.html` 한 파일.
- 테스트 (실제 GPT/Claude를 부르지 않음): `python tests/test_api.py`, `python tests/test_update.py`, `python tests/test_docs.py` (문서 버전 표기 검사)

| 파일 | 역할 |
|---|---|
| `ai_council_web.py` | 로컬 웹 서버(127.0.0.1:8765)와 API, `VERSION` |
| `web/index.html` | 채팅 UI, `UI_VERSION` |
| `council_core.py` | CLI 호출·제한 시간·중지·웹 검색·오류 안내 |
| `council_debate.py` | 토론 모드 프롬프트·행동 지침·중립 정리, 토론 기록 폴더 |
| `council_context.py` | 맥락 구성, 긴 대화 자동 요약 |
| `council_store.py` | 대화 저장·휴지통·검색·Markdown 내보내기 |
| `council_attach.py` / `council_media.py` | 첨부 처리 / 이미지·영상(ffmpeg) |
| `council_workflow.py` | ComfyUI 워크플로우 JSON 요약 |
| `council_state.py` | 사용 횟수, 계정 기본 모델 기억 |
| `council_mcp.py` | MCP 도구 목록 확인, 항상 허용 목록 |
| `council_commands.py` | 작업 모드 명령 허용 목록·승인 |
| `council_edit.py` | 작업 모드 Git 저장점·변경 확인·확정/되돌리기 |
| `council_i18n.py` | 서버 안내·오류 영어 번역 |
| `council_versions.py` | CLI 버전 확인·버튼 업데이트·로그인 |
| `council_update.py` | Council 자체 업데이트 (`Update.cmd` 가 화면 없이 실행) |
| `Setup.cmd` · `setup.ps1` | 처음 설치 도우미 (Windows) |
| `Setup-mac.command` · `AI-Council.command` · `Update-mac.command` | Mac 설치 · 실행 · 업데이트 |
| `AI-Council_Web.cmd` · `AI-Council_Debug.cmd` · `Update.cmd` | 실행 · 문제 확인용 실행 · 업데이트 |
| `AI-Council_CLI.ps1` | CLI 연결 확인용 PowerShell 스크립트 |
| `tests/` | 가짜 CLI(`fake_bin`)를 쓰는 테스트 |

---

<a id="english"></a>

# 🇺🇸 AI Council (English)

> **Current version: V0.16.0** · [Changelog (Korean)](CHANGELOG.md) · [한국어 설명은 위로 ↑](#ai-council)

**Ask GPT, Claude, or both at once — from one local chat window, using the subscriptions you already pay for.**

AI Council is a local multi-model chat app. For each question you pick **GPT**, **Claude**, or **Discussion** (both models debate, then a neutral summary).
It drives the official **Codex CLI (GPT)** and **Claude Code CLI (Claude)** signed in with your own ChatGPT / Claude subscription — **no API keys, no per-token billing**.

> 🌐 The app is available in **English and Korean**. It follows your browser language on first launch; switch any time with the `EN` / `한국어` button at the top left. The installer and update windows follow your Windows/Mac language. The models answer in whatever language you write in.

## 💡 Features

| Target | Best for | Model calls |
|---|---|---|
| **GPT** | Quick questions, prompt writing | 1 |
| **Claude** | Quick questions, file/workflow analysis | 1 |
| **Discussion** ⚠ | Design reviews and decisions with no single right answer | 5 (≈5× usage) |

- **Discussion mode** — round 1: both models answer independently · round 2: each critiques the other · final: a **blind, neutral synthesis** (the summarizer sees the answers only as "Model A / Model B", randomly assigned) split into *Conclusion / Agreed / Disagreed / Needs verification*. Every round is saved as Markdown in a local folder.
- **Two modes** — 💬 Chat (no file access) · 🛠 **Work** (like Claude Code / Codex: read, create and edit files, make folders, write code, run commands in the folder you choose)
- **Command allowlist + approval** — allowlisted commands (`mkdir`, `ls`, `git status` …) run right away; any other command is blocked and shown below the answer with **Allow once / Always allow / Don't allow**. Codex runs in its `workspace-write` sandbox (folder only, no internet).
- **Optional Git checkpoint** — if the folder is a Git repository, review the changed files and diff afterwards, then **commit** or **revert** with one click.
- **🌐 Web search** toggle — both models search the web and cite sources
- **🔌 MCP** (Claude) — use tools connected to your Claude account; only tools you allow run automatically, everything else asks for approval first
- **Attachments** — text/JSON, images, video (12 frames via ffmpeg); drag & drop or Ctrl+V. ComfyUI workflow JSON is pre-summarized (nodes, models, color-coded required inputs)
- **Conversation management** — auto titles, archive/trash, full-text search, long-conversation summaries, Markdown export per answer or per chat
- **English / 한국어** — switch with the `EN` / `한국어` button; installer and update windows follow your OS language
- **One-click updates** — for AI Council itself (from GitHub) and for both CLIs; dark / light / system theme; Windows and Mac

## 📦 Install

Requirements: a **ChatGPT** subscription (for GPT) and/or a **Claude Pro / Max** subscription (for Claude), and an internet connection.
Clone with `git` (not ZIP) so the built-in updater works.

**Windows**
1. `git clone https://github.com/eunjae-p/AI-Council.git`
2. Double-click **`Setup.cmd`**. It installs Python, Node.js, Git, ffmpeg (if missing), Codex CLI and Claude Code, walks you through sign-in, and creates an **AI Council** desktop shortcut.
3. Run **AI Council** from the desktop. If there is no red "Sign-in required" at the bottom left, you're ready.

**Mac**
1. Open Terminal and run `git clone https://github.com/eunjae-p/AI-Council.git` (accept the Xcode command-line tools prompt if asked).
2. Double-click **`Setup-mac.command`** (installs Homebrew if needed, then Python 3.10+, Node.js, ffmpeg and both CLIs). If macOS blocks it, right-click → Open once.
3. Double-click **AI Council** on the desktop.

**Sign-in** (once per computer): click the red **"Sign in"** link at the bottom left, or run in a terminal:

| Model | Command | Account |
|---|---|---|
| GPT | `codex login` (Windows PowerShell: `codex.cmd login`) | ChatGPT (Plus / Pro …) |
| Claude | `claude auth login` | Claude (Pro / Max; free plan not supported) |

## ▶ Run · update · stop

- **Run**: desktop shortcut (or `AI-Council_Web.cmd` / `AI-Council.command`). The server starts in the background and opens `http://127.0.0.1:8765` — reachable from this computer only.
- **Update**: when a new version exists, a yellow **⬆ Update** appears at the bottom left → **Update now**. Or run `Update.cmd` / `Update-mac.command`. Your conversations are kept.
- **Stop**: **Quit app** at the bottom left. Closing the browser tab leaves the server running.

## 🧭 Using it

- **Mode**: 💬 Chat (no file access) · 🛠 Work (reads, creates and edits files and runs commands in the working folder)
- **Target**: GPT · Claude · Discussion (both debate → neutral conclusion; *Show debate rounds* expands each round)
- **Work mode**: blocked commands show a 🛡 card — **Allow once and run again** / **Always allow and run again**. Manage the allowlist with **🛡** next to the folder. In a Git repository you can review changes and **✅ Commit** or **↩ Revert**; with uncommitted changes you choose **Create checkpoint and start** or **Continue without**.
- **Web search on/off**, **MCP on/off** (⚙ manages which tools are always allowed), **Models ▾** to pin model versions
- **⤓ MD** downloads one answer; **Chat_md** downloads the whole chat; **■ Stop** (or Esc) stops generating
- **Language**: `EN` / `한국어` at the top left. Saved messages are not translated; only Council's own labels and messages change.

## 🔒 Privacy

- Everything is stored locally in `data/` (conversations, attachments, debate logs) and `exports/`. Both are git-ignored and never uploaded to GitHub.
- The models still run in the cloud: your questions and attachments are sent to **OpenAI / Anthropic** under your own account's terms.
- AI Council never uses API keys and never falls back to an API when a CLI fails.

## 💻 For developers

- Python 3.10+ **standard library only**; the whole UI is a single file, `web/index.html`.
- Tests use fake CLIs (no real model calls): `python tests/test_api.py`, `python tests/test_update.py`, `python tests/test_docs.py`
- Contribution rules for humans and coding agents: [`CLAUDE.md`](CLAUDE.md) (= `AGENTS.md`, Korean).
