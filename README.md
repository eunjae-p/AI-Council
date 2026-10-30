# AI Council

**🇰🇷 한국어** · [🇺🇸 English](#english)

> **현재 버전: V0.20.1** (2026-10-30) · [전체 업데이트 내역 보기 → CHANGELOG.md](CHANGELOG.md)

하나의 채팅 화면에서 질문마다 **GPT / Claude / 토론(Discussion)** 을 골라 답을 받는 로컬 멀티모델 채팅 앱입니다.
각 PC에서 **구독 계정으로 로그인한 Codex CLI(GPT)와 Claude Code CLI(Claude)** 를 사용하며, API 키는 쓰지 않습니다.

## 🆕 최근 업데이트

| 버전 | 날짜 | 주요 변경 |
|---|---|---|
| [V0.20.1](CHANGELOG.md#v0201-2026-10-30) | 10-30 | 토론 결론 위에 **📁 토론 기록 폴더** 버튼 (열기 + 경로 복사) |
| [V0.20.0](CHANGELOG.md#v0200-2026-10-30) | 10-30 | **🔁 Claude 데스크톱 앱과 번갈아 쓰기** — HANDOFF.md 자동 기록, 📄 CLAUDE.md 준비, 🖥 Claude 앱에서 이어서 |
| [V0.19.2](CHANGELOG.md#v0192-2026-10-29) | 10-29 | 작업 모드 시간 제한: 진행 중이면 계속(15분 무응답·60분 상한), 멈춰도 **↪ 이어서 진행** |
| [V0.19.1](CHANGELOG.md#v0191-2026-10-29) | 10-29 | 작업 모드: 승인이 필요하면 **그 자리에서 멈춤**(⏸), 토론+작업도 실행 세션만 이어서, 개발 명령 허용 표시 개선 |
| [V0.19.0](CHANGELOG.md#v0190-2026-10-29) | 10-29 | **💰 토큰 절약** — 캐시가 맞게 맥락 고정, 지난 토론은 결론만, 🪙 토큰 표시, 💰 절약 모드 |

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

## 📂 폴더에서 바로 찾는 실행 파일

폴더를 열면 맨 위에 번호 순서대로 보입니다. Windows는 `(Windows).cmd`, Mac은 `(Mac).command` 를 더블클릭하세요.

| 파일 | 하는 일 |
|---|---|
| **`0_처음 설치 (Windows).cmd`** / `(Mac).command` | 처음 한 번: 필요한 프로그램 설치, 로그인, 바탕화면 바로가기 |
| **`1_AI Council 실행 (Windows).cmd`** / `(Mac).command` | AI Council 실행 (바탕화면 바로가기와 같음) |
| **`2_업데이트 (Windows).cmd`** / `(Mac).command` | GitHub 최신 버전 받기 (화면의 업데이트 버튼과 같음) |

기존 파일(`Setup.cmd`, `AI-Council_Web.cmd`, `Update.cmd` 등)도 그대로 동작합니다. 위 파일은 그 파일을 대신 실행해 주는 바로가기입니다.

## 📦 처음 설치하기 (팀원용)

각자 자기 PC에서, 자기 구독 계정으로 씁니다. 대화 기록은 각자 PC에만 저장되고 공유되지 않습니다.
필요한 것: ChatGPT 구독(GPT) 그리고/또는 Claude Pro·Max 구독(Claude), 인터넷 연결.

1. 원하는 폴더에서 저장소를 받습니다. **ZIP이 아니라 `git clone`** 으로 받아야 자동 업데이트가 됩니다.
   ```powershell
   git clone https://github.com/eunjae-p/AI-Council.git
   ```
2. 받은 폴더의 **`0_처음 설치 (Windows).cmd`** (= `Setup.cmd`) 를 더블클릭합니다. 자동으로:
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
2. Finder에서 받은 폴더의 **`0_처음 설치 (Mac).command`** (= `Setup-mac.command`) 를 더블클릭합니다. 자동으로:
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

**계정 바꾸기** (같은 PC에서 다른 계정 사용): 왼쪽 아래 Codex·Claude 줄의 **↻ 계정 바꾸기** → 로그인 창에서 로그아웃 후 자동으로 다시 로그인이 시작됩니다.
- 브라우저가 기존 계정으로 로그인돼 있으면 그 계정이 다시 연결될 수 있습니다 → 브라우저에서 먼저 로그아웃하거나, 로그인 창에 나온 주소를 시크릿 창에 붙여 넣으세요.
- 터미널로 직접: `codex.cmd logout` → `codex.cmd login`, `claude auth logout` → `claude auth login`
- 대화 기록·명령 허용 목록·MCP 등록은 PC에 저장돼 있어 그대로 남습니다.

## ▶ 실행 · 종료

- **실행**: 바탕화면 **AI Council** (또는 폴더의 **`1_AI Council 실행 (Windows).cmd`**). 창 없이 백그라운드로 켜지고 브라우저에서 `http://127.0.0.1:8765` 가 열립니다. 이 PC에서만 접속됩니다.
- **종료**: 화면 왼쪽 아래 **앱 종료**. 브라우저 탭만 닫으면 서버는 계속 켜져 있고, 바로가기를 다시 누르면 화면만 다시 열립니다.
- **문제 확인용 실행**: `AI-Council_Debug.cmd` (콘솔 창에 서버 메시지 표시). 백그라운드 기록은 `data/logs/server.log`.

## 🔄 Council 업데이트

GitHub의 최신 버전을 받는 방법은 두 가지입니다. 대화 기록은 그대로 유지됩니다.

1. **화면에서**: 새 버전이 있으면 왼쪽 아래 Council 버전 아래에 노란 **⬆ 업데이트하기** → **지금 업데이트** (자동 재시작·새로고침)
2. **화면 없이**: 폴더의 **`2_업데이트 (Windows).cmd`** (Mac: `2_업데이트 (Mac).command`) 더블클릭 → `Y`

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
   **이번만 허용하고 다시 실행 / 항상 허용하고 다시 실행 / 허용 안 함**.
   막힌 명령·MCP 도구가 나오면 Claude 는 **그 자리에서 멈춥니다** (⏸ 표시 — 막힌 단계를 건너뛰고 다음 작업을 하지 않음).
   허용하면 **멈춘 Claude 세션을 그대로 이어서** 그 단계부터 실행합니다 (앞에서 읽은 파일·실행 결과를 기억, 처음부터 다시 하지 않음).
   토론 + 작업 모드에서 Claude 가 실행 단계에서 멈춘 경우도 토론을 다시 하지 않고 그 세션만 이어서 진행합니다.
   승인은 빨리 할수록 쌉니다 — 1시간 안이면 이전 기록을 캐시에서 읽습니다 (🔔 알림을 켜 두세요).
   **시간 제한**: 진행 상황이 계속 나오면 기다리고, **15분 동안 아무 진행이 없거나 60분**이 넘으면 멈춥니다.
   멈춰도 작업은 버리지 않습니다 — **⏱ 시간 제한으로 멈췄습니다 · ↪ 이어서 진행** 을 누르면 그 세션에서 계속합니다.
   기본 허용 목록에는 `cat`·`ls`·`grep`·`sha1sum`·`cut`·`diff`·`git show` 같은 **읽기 전용 명령**이 들어 있습니다. `for … do … done` 반복문은 허용 목록으로 허용할 수 없어, Claude에게 단순한 명령으로 나눠 실행하도록 안내합니다.
3. 허용 목록 관리: 작업 폴더 옆 **🛡** 버튼 (추가·삭제·기본값으로, **개발 명령 한 번에 허용** = node·npm·npx·python·pip·uv·git — 누르면 방금 추가된 명령이 맨 위에 표시되고 버튼이 **✓ 개발 명령 허용됨**으로 바뀝니다). `python`·`node`·`rm`·`curl` 처럼 사실상 무엇이든 할 수 있는 명령은 빨간 표시가 붙습니다.
4. **진행 상황**: Claude가 지금 쓰는 도구·명령(🔌 블렌더 · execute_blender_code, `$ npm install` 등)이 진행 표시 아래에 실시간으로 나오고, 끝나면 답변의 **작업 기록 보기**에 남습니다.
5. **저장점(선택)**: 작업 폴더가 Git 저장소면 끝난 뒤 **📝 변경된 파일** 카드 → **✅ 확정 (커밋)** / **↩ 되돌리기**.
   저장 안 된 변경이 있으면 시작 전에 "저장점 만들고 시작 / 저장점 없이 진행"을 고릅니다. Git 저장소가 아닌 폴더(예: `D:\` 아래 새 폴더)는 그냥 진행합니다.

- **GPT(Codex)**: `workspace-write` 샌드박스 — 작업 폴더 안에서만 쓰고, 명령 실행과 **인터넷(설치 등)은 허용**됩니다. Codex는 명령별 승인을 할 수 없어 폴더 범위로 제한합니다.
- **블렌더 등 연결된 도구**: 모드와 별개로 **🔌 Claude MCP** / **🔌 GPT MCP** 를 켭니다 (각 CLI에 Blender MCP가 등록돼 있어야 함).
- **토론 + 작업 (협업)**: ① GPT·Claude가 **읽기만 하며** 계획 토론 → ② 결론 → ③ **실행: Claude / 실행: GPT** 로 고른 모델이 작업 →
  ④ 다른 모델이 결과(파일·블렌더 씬)를 **읽기 전용으로 검토** → ⑤ 문제가 있으면 실행한 모델이 수정 (검토가 `LGTM`이면 생략).
  같은 파일·같은 블렌더 씬을 동시에 고치지 않도록 순서대로 주고받습니다. 기록은 `3_구현`·`4_검토`·`5_수정.md`.
- **서버 실행**: 오래 켜 두는 서버는 백그라운드로 실행하도록 지시합니다. 끄는 방법은 답변에 안내됩니다.
- ⚠ **운영 중인 서비스 폴더는 복사본에서** 작업하고 확인 후 반영하는 것을 권장합니다. 모든 명령을 묻지 않고 실행하는 모드는 쓰지 않습니다.

### 🔁 Claude 데스크톱 앱과 번갈아 쓰기
세션(대화)을 넘기기보다 **같은 작업 폴더 + 인수인계 기록**으로 이어 가는 방식입니다.
1. 작업 폴더 옆 **📄** → `CLAUDE.md` 준비 (없으면 프로젝트 안내 틀, 있으면 "HANDOFF.md 에 기록" 규칙만 덧붙임).
   Claude Code(데스크톱 앱·터미널·Council 작업 모드)는 작업 폴더의 `CLAUDE.md` 를 자동으로 읽습니다. 짧게 유지하세요.
2. **📝 인수인계 켬** (기본): 작업 모드가 끝나면 Council 이 `HANDOFF.md` 에 요청·실행 모델·상태·바뀐 파일·세션 ID·결과 요약을 덧붙입니다.
   파일을 읽기만 한 질문은 기록하지 않습니다. ⚠ 웹 서버가 그대로 공개하는 폴더(운영 중인 사이트 폴더 등)라면 끄세요.
3. Claude 작업 답변의 **🖥 Claude 앱에서 이어서**: 데스크톱 앱에서 그 세션을 바로 엽니다 (`claude://resume?session=…`, 공식 문서에 없는 링크).
   안 열리면 데스크톱 앱 Code 화면에서 `/resume` → 세션 선택, 또는 복사된 터미널 명령 `claude --resume <ID>`.
4. 앱에서 한 작업은 Council 대화에 들어오지 않습니다. Council 로 돌아올 때는 **"HANDOFF.md 마지막 항목 보고 이어서 해줘"**.
- 같은 폴더를 Council 과 앱에서 **동시에** 작업시키지 마세요. Git 저장소면 넘기기 전에 ✅ 확정(커밋)해 두면 안전합니다.

### 🎨 이미지 모드
- 입력창 위 **🎨 이미지** → 비율(1:1 · 가로 · 세로)·장수(1~4) → **저장 폴더** 입력(비우면 Council 폴더의 `exports\images\날짜`) → 만들 이미지를 설명하고 보내기.
- **GPT**: Codex CLI의 이미지 생성 도구로 바로 생성. **Claude / 토론**: Claude가 이미지 프롬프트를 다듬고 → GPT가 생성 (Claude에는 이미지 생성 모델이 없음).
- 결과는 저장 폴더에 `council_날짜_시각_1.png …`로 저장되고, 채팅 화면에도 표시됩니다 (**📁 폴더 열기**). 📎로 이미지를 첨부하면 참고 이미지로 씁니다.
- ChatGPT **Plus 이상** 구독 필요 (구독 사용량, API 키 없음). 장당 30초~1분, 텍스트 질문보다 사용량이 큽니다.
- 이미지가 안 만들어지면 경고가 뜹니다 → 왼쪽 아래에서 Codex CLI를 최신으로 업데이트한 뒤 다시 시도하세요.

### 토론 (Discussion) ⚠
1. **1라운드 독립 의견** — GPT·Claude가 서로의 답을 보지 않고 동시에 답합니다.
2. **2라운드 교차 검토** — 각자 상대 답을 읽고 동의·반박·누락·입장 변화를 씁니다.
3. **최종 결론** — **결론 / 합의된 점 / 의견이 갈린 점 / 확인이 필요한 항목** 으로 정리합니다.

- **행동 지침**: 근거로만 판단하고(새 근거 없이 양보·반대 금지), 확신도를 밝히고, 둘 다 검증하지 않은 공통 가정을 따로 표시합니다.
- **중립 정리**: 결론을 정리하는 Claude는 두 답변을 이름을 가린 채(모델 A/B, 무작위) 받아 자기 답을 편들지 못합니다.
- 화면에는 결론이 먼저, **토론 과정 보기** 를 펼치면 라운드별 답변이 보입니다. 결론 위쪽의 **📁 토론 기록 폴더** 로 PC에 저장된 기록(`결론.md` 등)을 열고 경로도 복사합니다 — Claude 데스크톱 앱에 "이 폴더의 결론.md 읽고 구현해줘"로 붙여넣기.
- **읽는 법**: 두 모델이 합의했다고 정답은 아닙니다. **"의견이 갈린 점"과 "확인이 필요한 항목"** 을 먼저 확인하세요.
- 사용량이 단독의 약 5배입니다 (💰 절약 모드에서는 3번 호출). 간단한 질문·워크플로우 분석·프롬프트 작성은 단독 모델이 효율적입니다.

### 💰 토큰(사용량) 절약
구독 한도는 결국 **토큰**으로 줄어듭니다. 질문 하나마다 Council 이 보내는 것 = 대화 맥락 + 첨부 + 지시문이고, CLI 는 여기에 자기 시스템 프롬프트·도구 설명(MCP 를 켜면 그 도구 설명까지)을 붙입니다.
출력(답변·생각) 토큰이 입력보다 몇 배 비싸고, **앞부분이 직전 호출과 같은 입력은 캐시에서 읽어 훨씬 싸게** 계산됩니다.

자동으로 하는 것 (항상)
- **맥락 앞부분 고정**: 최근 대화 창의 시작을 고정해 두고 넘칠 때만 옮깁니다 → 매 질문마다 프롬프트 앞부분이 같아 캐시가 맞습니다.
- **지난 토론은 결론만**: 두 모델의 1라운드 답변은 가장 최근 토론에서만 맥락에 넣습니다 (교차 검토는 원래 제외).
- **결론 정리는 짧은 맥락**: 토론 결론 단계는 최근 대화 약 6천 자만 봅니다 (두 모델 답이 이미 맥락을 반영).
- **이미지 재전송 줄이기**: 이미지·영상(프레임 12장)은 바로 다음 질문이거나 질문에 "이미지·영상·화면·프레임…"이 있을 때만 다시 보냅니다.
- **🪙 토큰 표시**: 답변마다 이번 호출 토큰(마우스를 올리면 새 입력 / 캐시 읽기 / 출력), 왼쪽 아래에 오늘 GPT·Claude 토큰 합계.

**💰 절약 켬** (입력창 위, 필요할 때만)
- 토론: 교차 검토(2라운드) 생략 → 5번 → **3번 호출**
- 최근 대화 맥락 약 1만 자, 첨부 원문 3만 자까지
- 답변을 간결하게 요청 (출력 토큰 절약)
- GPT 대화: 생각(추론) 강도 `low` — 작업 모드는 그대로

더 아끼는 습관: 간단한 질문은 토론 대신 단독 · MCP 는 쓸 때만 켜기(켜 두면 매번 도구 설명이 붙음) · 주제가 바뀌면 **↪ 새 대화로 이어가기**.

### 🌐 웹 검색
- 입력창 위 **웹 검색 켬/끔**. 켜면 GPT(Codex `--search`)·Claude(WebSearch·WebFetch)가 웹을 검색하고 출처를 밝힙니다.
- 가격·API·약관처럼 바뀔 수 있는 정보에 켜세요. 답변 시간과 사용량이 늘어납니다.

### 🔌 MCP (연결된 도구)
- 입력창 위 **🔌 Claude MCP** / **🔌 GPT MCP** (각각 켬/끔, 기본 꺼짐).
  - **Claude MCP**: Claude 계정(claude.ai 커넥터)·Claude Code에 연결된 도구(예: Blender, Higgsfield, Notion). 아래처럼 도구별 허용.
  - **GPT MCP**: Codex에 등록된 도구 (`~/.codex/config.toml`, Codex 데스크톱 앱에서 연결한 Blender 등). Codex는 도구별 허용을 고를 수 없어 **켜면 모두 켜집니다**.
- **블렌더 연결**: Claude Code에 등록 (PowerShell에서는 `--`를 따옴표로): `claude mcp add -s user blender '--' uv run --directory D:\tools\blender_mcp\mcp blender-mcp` → `claude mcp list` 에 `blender ✓ Connected`.
- **⚙ (MCP 도구 관리)** → **도구 목록 가져오기** → 바로 실행해도 되는 도구 또는 **서버 전체**에 **"항상 허용"** 체크. 조회 도구(잔액·내역 조회 등)만 허용해 두는 것을 권장합니다.
- 허용하지 않은 도구를 Claude가 쓰려 하면 **실행하지 않고** 답변 아래에 도구·입력 내용을 보여 줍니다 → **이번만 허용 / 항상 허용 / 허용 안 함**.
- ⚠ 생성·수정·결제처럼 크레딧이 들 수 있는 도구는 빨간 **실행·비용 가능** 표시가 붙습니다. 입력 내용을 확인하고 허용하세요.

### 첨부 (📎 · 끌어다 놓기 · Ctrl+V)
| 종류 | 형식 · 크기 | 처리 |
|---|---|---|
| 텍스트·JSON | json, txt, md, py 등 · 2MB, 최대 5개 | ComfyUI 워크플로우는 코드가 노드·**색상 등급**·모델·노드 팩·서브그래프를 먼저 요약 |
| 이미지 | png, jpg, webp, gif, bmp · 20MB | 모델이 직접 봅니다 |
| 영상 | mp4, mov, mkv, webm 등 · 2GB | ffmpeg로 프레임 12장 + 길이·해상도·fps 정보 (소리는 분석 안 함) |
| ZIP | zip · 500MB | 안전하게 풀어서 **파일 목록 + 텍스트·코드 내용**(README 먼저, 약 8만 자까지) + 안의 이미지 최대 8장 전달. 워크플로우 JSON은 요약. 작업 모드에서는 풀린 폴더를 직접 열어 볼 수 있음 |

ZIP 안의 `__MACOSX`·`.git`·`node_modules`, 폴더 밖을 가리키는 경로, 바로가기(링크), 암호 걸린 파일은 풀지 않습니다. Windows에서 만든 ZIP의 한글 파일 이름도 깨지지 않습니다.

워크플로우 색상 등급: 빨강 = MUST, 노랑·주황 = SHOULD (판정 제외: MarkdownNote, Note, Label (rgthree), SetNode, GetNode).

### 화면 안내
- **🔔 알림**: 왼쪽 위 🔔/🔕. 다른 창·탭을 보고 있을 때 답변이 끝나면(또는 승인이 필요하면) 데스크톱 알림. 알림을 누르면 그 대화로 이동. 처음 보낼 때 브라우저가 알림 허용을 묻습니다 (차단했다면 주소창 왼쪽 자물쇠 → 알림 허용).
- **화면 언어**: 왼쪽 위 `EN` / `한국어` 버튼. 처음에는 브라우저 언어를 따릅니다(한국어가 아니면 영어). 대화 기록 원문은 바뀌지 않고, Council 안내·오류 문구만 바뀝니다. 설치·업데이트 창은 Windows/Mac 언어를 따릅니다.
- **화면 테마**: 왼쪽 위 `AI Council` 옆 🌙/☀️/🖥️ 버튼으로 다크·라이트·시스템 설정 따르기를 바꿉니다.
- **모델 표시**: 계정 기본값을 써도 실제 모델 이름이 보입니다 (예: `GPT-6.1 Sol (계정 기본)`).
- **왼쪽 아래**: CLI 버전·업데이트·로그인 상태·↻ 계정 바꾸기, 오늘 사용 횟수·🪙 토큰, **남은 사용량 보기** (공식 사용량 페이지).
- **대화 목록 아이콘**: 💬 대화 모드 · 🔧 작업 모드 · `GPT`/`Claude` 배지 = 그 대화에서 답한 모델.
- **긴 대화**: 화면에는 최근 질문 12묶음만 그리고, 위의 **⬆ 이전 메시지 더 보기 / 전체 보기**로 더 불러옵니다 (렉 방지).
  - **🗜 압축**: 지금까지의 대화를 바로 요약으로 압축 (최근 대화는 원문 유지, 원문 기록은 지우지 않음). 모델에 보내는 맥락은 원래도 자동으로 압축됩니다(장기 요약).
  - **↪ 새 대화로 이어가기**: 대화 전체를 요약해 그 요약을 기억하는 새 대화를 시작. 메시지가 150개를 넘으면 위에 안내가 뜹니다. 두 대화는 서로 링크로 연결.
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
| 작업 모드에서 오래 걸리는데 아무 변화가 없음 | 진행 표시 아래 실시간 기록 확인: `MCP:` 줄에 blender 가 없으면 Claude Code에 Blender MCP 미등록, 도구 호출이 없으면 웹 검색만 하는 중일 수 있음 (블렌더 작업은 웹 검색 끔 권장) |
| `Failed to authenticate: OAuth session expired` / 로그인 만료 | 왼쪽 아래 **버전 다시 확인** → 빨간 **로그인하기** (또는 터미널 `claude auth login` / `codex login`) 후 다시 보내기 |
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
| `council_attach.py` / `council_media.py` / `council_archive.py` | 첨부 처리 / 이미지·영상(ffmpeg) / ZIP 풀기 |
| `council_handoff.py` | 작업 폴더 HANDOFF.md 인수인계 기록, CLAUDE.md 준비 |
| `council_workflow.py` | ComfyUI 워크플로우 JSON 요약 |
| `council_state.py` | 사용 횟수, 계정 기본 모델 기억 |
| `council_mcp.py` | MCP 도구 목록 확인, 항상 허용 목록 |
| `council_commands.py` | 작업 모드 명령 허용 목록·승인 |
| `council_edit.py` | 작업 모드 Git 저장점·변경 확인·확정/되돌리기 |
| `council_image.py` | 🎨 이미지 생성 결과 저장 |
| `council_i18n.py` | 서버 안내·오류 영어 번역 |
| `council_versions.py` | CLI 버전 확인·버튼 업데이트·로그인 |
| `council_update.py` | Council 자체 업데이트 (`Update.cmd` 가 화면 없이 실행) |
| `Setup.cmd` · `setup.ps1` | 처음 설치 도우미 (Windows) |
| `Setup-mac.command` · `AI-Council.command` · `Update-mac.command` | Mac 설치 · 실행 · 업데이트 |
| `AI-Council_Web.cmd` · `AI-Council_Debug.cmd` · `Update.cmd` | 실행 · 문제 확인용 실행 · 업데이트 |
| `0_처음 설치` · `1_AI Council 실행` · `2_업데이트` (`.cmd` / `.command`) | 위 파일을 대신 실행하는 한글 이름 바로가기 |
| `AI-Council_CLI.ps1` | CLI 연결 확인용 PowerShell 스크립트 |
| `tests/` | 가짜 CLI(`fake_bin`)를 쓰는 테스트 |

---

<a id="english"></a>

# 🇺🇸 AI Council (English)

> **Current version: V0.20.1** · [Changelog (Korean)](CHANGELOG.md) · [한국어 설명은 위로 ↑](#ai-council)

**Ask GPT, Claude, or both at once — from one local chat window, using the subscriptions you already pay for.**

AI Council is a local multi-model chat app. For each question you pick **GPT**, **Claude**, or **Discussion** (both models debate, then a neutral summary).
It drives the official **Codex CLI (GPT)** and **Claude Code CLI (Claude)** signed in with your own ChatGPT / Claude subscription — **no API keys, no per-token billing**.

> 🌐 The app is available in **English and Korean**. It follows your browser language on first launch; switch any time with the `EN` / `한국어` button at the top left. The installer and update windows follow your Windows/Mac language. The models answer in whatever language you write in.

## 💡 Features

| Target | Best for | Model calls |
|---|---|---|
| **GPT** | Quick questions, prompt writing | 1 |
| **Claude** | Quick questions, file/workflow analysis | 1 |
| **Discussion** ⚠ | Design reviews and decisions with no single right answer | 5 (≈5× usage; 3 in 💰 Saver mode) |

- **Discussion mode** — (📁 *Discussion log folder* on the conclusion opens the saved Markdown files and copies the path) round 1: both models answer independently · round 2: each critiques the other · final: a **blind, neutral synthesis** (the summarizer sees the answers only as "Model A / Model B", randomly assigned) split into *Conclusion / Agreed / Disagreed / Needs verification*. Every round is saved as Markdown in a local folder.
- **Two modes** — 💬 Chat (no file access) · 🛠 **Work** (like Claude Code / Codex: read, create and edit files, make folders, write code, run commands in the folder you choose)
- **Command allowlist + approval** — allowlisted commands (`mkdir`, `ls`, `git status` …) run right away; any other command is blocked and shown below the answer with **Allow once / Always allow / Don't allow**. Codex runs in its `workspace-write` sandbox (writes inside the folder only; internet allowed for installs).
- **Optional Git checkpoint** — if the folder is a Git repository, review the changed files and diff afterwards, then **commit** or **revert** with one click.
- **🌐 Web search** toggle — both models search the web and cite sources
- **🎨 Image mode** — GPT generates real images (Codex image tool, ChatGPT Plus or higher) and saves PNGs to the folder you choose; shown in the chat too. With Claude/Discussion, Claude writes the prompt and GPT generates.
- **🔌 Claude MCP / GPT MCP** — use connected tools such as Blender with either model. Claude: only tools you allow run automatically, others ask first. GPT: all tools registered in Codex are enabled when on.
- **Collaboration** — Discussion + Work: both plan → the model you pick (**Run: Claude / Run: GPT**) executes → the other reviews the actual result read-only → the executor fixes.
- **Attachments** — text/JSON, images, video (12 frames via ffmpeg), ZIP (safely extracted: file list, text/code contents, up to 8 images; in work mode the extracted folder can be opened); drag & drop or Ctrl+V. ComfyUI workflow JSON is pre-summarized (nodes, models, color-coded required inputs)
- **💰 Token saving** — always on: the start of the recent-context window stays fixed so each prompt begins like the previous one and hits the CLIs' prompt cache (cached input counts much cheaper); older discussions keep only the conclusion; the final summary uses a short context; images are re-sent only when the question is about them. Every answer shows 🪙 tokens (new input / cached input / output), with daily totals at the bottom left. Optional **💰 Saver** toggle: skips the discussion cross review (5 → 3 calls), shorter context and attachment excerpts, concise answers, low reasoning effort for GPT in chat.
- **🔁 Switching with the Claude desktop app** — 📄 prepares `CLAUDE.md` (template, or just appends the handoff rule); 📝 Handoff (on by default) appends request / status / changed files / session ID / result summary to `HANDOFF.md` in the working folder after each Work task (read-only questions are skipped; turn it off for folders a web server publishes); **🖥 Continue in Claude app** opens the session in the desktop app via `claude://resume?session=…` (undocumented link; fallback: `/resume` in the app or the copied `claude --resume <ID>`). Back in Council, say "read the last entry of HANDOFF.md and continue".
- **Conversation management** — auto titles, archive/trash, full-text search, long-conversation summaries, Markdown export per answer or per chat
- **English / 한국어** — switch with the `EN` / `한국어` button; installer and update windows follow your OS language
- **One-click updates** — for AI Council itself (from GitHub) and for both CLIs; dark / light / system theme; Windows and Mac

## 📦 Install

Requirements: a **ChatGPT** subscription (for GPT) and/or a **Claude Pro / Max** subscription (for Claude), and an internet connection.
Clone with `git` (not ZIP) so the built-in updater works.

**Windows**
1. `git clone https://github.com/eunjae-p/AI-Council.git`
2. Double-click **`0_처음 설치 (Windows).cmd`** ("first-time setup", same as `Setup.cmd`). It installs Python, Node.js, Git, ffmpeg (if missing), Codex CLI and Claude Code, walks you through sign-in, and creates an **AI Council** desktop shortcut.
3. Run **AI Council** from the desktop. If there is no red "Sign-in required" at the bottom left, you're ready.

**Mac**
1. Open Terminal and run `git clone https://github.com/eunjae-p/AI-Council.git` (accept the Xcode command-line tools prompt if asked).
2. Double-click **`0_처음 설치 (Mac).command`** (same as `Setup-mac.command`) (installs Homebrew if needed, then Python 3.10+, Node.js, ffmpeg and both CLIs). If macOS blocks it, right-click → Open once.
3. Double-click **AI Council** on the desktop.

**Sign-in** (once per computer): click the red **"Sign in"** link at the bottom left, or run in a terminal:

| Model | Command | Account |
|---|---|---|
| GPT | `codex login` (Windows PowerShell: `codex.cmd login`) | ChatGPT (Plus / Pro …) |
| Claude | `claude auth login` | Claude (Pro / Max; free plan not supported) |

**Switch account** (another account on the same computer): click **↻ Switch account** next to Codex or Claude at the bottom left. A terminal window signs you out and starts sign-in again. If your browser is still signed in with the old account, sign out there first or paste the sign-in URL into a private window. Terminal: `codex logout` → `codex login`, `claude auth logout` → `claude auth login`. Chats, the command allowlist and MCP servers stay as they are.

## ▶ Run · update · stop

- **Run**: desktop shortcut (or `1_AI Council 실행 (Windows).cmd` / `(Mac).command` — "start"; same as `AI-Council_Web.cmd` / `AI-Council.command`). The server starts in the background and opens `http://127.0.0.1:8765` — reachable from this computer only.
- **Update**: when a new version exists, a yellow **⬆ Update** appears at the bottom left → **Update now**. Or run `2_업데이트 (Windows).cmd` / `(Mac).command` ("update"; same as `Update.cmd` / `Update-mac.command`). Your conversations are kept.
- **Stop**: **Quit app** at the bottom left. Closing the browser tab leaves the server running.

## 🧭 Using it

- **Mode**: 💬 Chat (no file access) · 🛠 Work (reads, creates and edits files and runs commands in the working folder)
- **Target**: GPT · Claude · Discussion (both debate → neutral conclusion; *Show debate rounds* expands each round)
- **Work mode**: when a command or MCP tool is blocked, Claude **pauses right there** (⏸, nothing after it runs) and a 🛡 card appears — **Allow once and run again** / **Always allow and run again** resumes the same Claude session from that step (also for the executor step in Discussion + Work, without rerunning the discussion). Approve soon: within about an hour the earlier history is read from cache. Time limit: Claude keeps going while it reports progress; it stops after 15 minutes with no progress or 60 minutes in total, and **↪ Continue** resumes the same session (work is not thrown away). Manage the allowlist with **🛡** next to the folder. In a Git repository you can review changes and **✅ Commit** or **↩ Revert**; with uncommitted changes you choose **Create checkpoint and start** or **Continue without**.
- **💰 Saver on/off** (fewer tokens: see Features), **Web search on/off**, **Claude MCP / GPT MCP on/off** (⚙ manages Claude's always-allowed tools), **Run: Claude / Run: GPT** in Discussion + Work, **Models ▾** to pin model versions
- **⤓ MD** downloads one answer; **Chat_md** downloads the whole chat; **■ Stop** (or Esc) stops generating
- **Long chats**: only the latest 12 turns are drawn (⬆ show earlier / show all); **🗜 Compress** summarizes the chat now; **↪ Continue in new chat** starts a new chat that carries over a summary.
- **🔔 Notifications**: desktop notification when an answer is ready (or needs approval) while you're in another window; toggle with 🔔/🔕 at the top left.
- **Language**: `EN` / `한국어` at the top left. Saved messages are not translated; only Council's own labels and messages change.

## 🔒 Privacy

- Everything is stored locally in `data/` (conversations, attachments, debate logs) and `exports/`. Both are git-ignored and never uploaded to GitHub.
- The models still run in the cloud: your questions and attachments are sent to **OpenAI / Anthropic** under your own account's terms.
- AI Council never uses API keys and never falls back to an API when a CLI fails.

## 💻 For developers

- Python 3.10+ **standard library only**; the whole UI is a single file, `web/index.html`.
- Tests use fake CLIs (no real model calls): `python tests/test_api.py`, `python tests/test_update.py`, `python tests/test_docs.py`
- Contribution rules for humans and coding agents: [`CLAUDE.md`](CLAUDE.md) (= `AGENTS.md`, Korean).
