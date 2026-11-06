# AI Council

**🇰🇷 한국어** · [🇺🇸 English](#english)

> **현재 버전: V0.27.0** (2026-11-06) · [전체 업데이트 내역 보기 → CHANGELOG.md](CHANGELOG.md)

하나의 채팅 화면에서 질문마다 **GPT / Claude / 토론(Discussion)** 을 골라 답을 받는 로컬 멀티모델 채팅 앱입니다.
각 PC에서 **구독 계정으로 로그인한 Codex CLI(GPT)와 Claude Code CLI(Claude)** 를 사용하며, API 키는 쓰지 않습니다.

## 🆕 최근 업데이트

| 버전 | 날짜 | 주요 변경 |
|---|---|---|
| [V0.27.0](CHANGELOG.md#v0270-2026-11-06) | 11-06 | 🖥 **앱처럼 실행** — 아이콘을 누르면 주소창 없는 **앱 창**으로 열림, 바탕화면·시작 메뉴(Mac: 응용 프로그램) 바로가기 |
| [V0.26.0](CHANGELOG.md#v0260-2026-11-04) | 11-04 | 🎨 **이미지 모드 → 대화 모드로 통합** — 비율(기본 16:9·묻기)·장수, ⚙ 환경설정(저장 폴더, 기본 `image`), ⬇ 다운로드 |
| [V0.25.0](CHANGELOG.md#v0250-2026-11-04) | 11-04 | 🛠 작업 모드 **📁＋ 추가 폴더** — 작업 폴더 말고도 여러 폴더를 함께 읽고 고치기 |
| [V0.24.1](CHANGELOG.md#v0241-2026-11-04) | 11-04 | 응답 중 **연결 끊김(network error)** 대처 — 서버 꺼짐/작업 계속 중 안내·자동 표시, 연결 유지 신호, Council 종료 방지 |
| [V0.24.0](CHANGELOG.md#v0240-2026-11-04) | 11-04 | **🎨 대화 중 이미지** — 대화 모드에서 GPT 가 이미지를 만들어 보여 주고 이어서 고치기, 빈 빨간 띠 수정 |

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

- **실행**: 바탕화면·시작 메뉴의 **AI Council** 아이콘 (Mac: 응용 프로그램의 **AI Council** 앱, 또는 폴더의 **`1_AI Council 실행`**).
  서버가 창 없이 백그라운드로 켜지고, Council 이 **앱 창**(주소창·탭 없는 독립 창, Edge/Chrome 사용)으로 열립니다. 이미 켜져 있으면 창만 다시 엽니다. 이 PC에서만 접속됩니다.
  - **아이콘 만들기**: 처음 설치 때 자동으로 만들어집니다. 이미 설치한 PC 는 **⚙ 환경설정 → 바로가기 만들기**.
  - **작업 표시줄에 고정**(Windows): 시작 메뉴의 AI Council 을 오른쪽 클릭 → **작업 표시줄에 고정**. Mac 은 응용 프로그램의 AI Council 을 Dock 에 끌어다 놓기.
  - 앱 창 대신 브라우저 탭으로 열고 싶으면 **⚙ 환경설정 → 창 열기: 브라우저 탭**. Edge·Chrome 이 없으면 자동으로 브라우저 탭으로 엽니다.
- **종료**: 화면 왼쪽 아래 **앱 종료**. 앱 창(또는 탭)만 닫으면 서버는 계속 켜져 있고, 아이콘을 다시 누르면 화면만 다시 열립니다.
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
   다른 폴더도 함께 다루려면 작업 폴더 옆 **📁＋** → 추가 폴더 입력 (여러 개는 `;` 로 구분, 예: `D:\shared; E:\assets`, 최대 10개).
   추가 폴더도 읽고 고칠 수 있고(GPT·Claude 모두), 명령 실행 위치·`HANDOFF.md`·Git 저장점은 첫 번째 작업 폴더 기준입니다.
2. **명령 실행은 허용 목록 + 승인**: `mkdir`, `ls`, `git status` 같은 명령은 바로 실행됩니다.
   목록에 없는 명령(예: `npm install`, `python app.py`)은 실행하지 않고 답변 아래에 **🛡 승인 카드**가 뜹니다 →
   **이번만 허용하고 다시 실행 / 항상 허용하고 다시 실행 / 허용 안 함**.
   **허용했는데도 막히면**(Claude Code 자체 안전 검사 — 작업 폴더 밖 경로·드라이브 전체·보호 폴더 등) 같은 카드를 반복하지 않고 **⚠ 이유와 해결 방법**을 보여 줍니다.
   작업 폴더는 드라이브 전체(`D:\`)보다 **프로젝트 폴더**(`D:\VQC`)를 쓰세요 — 드라이브 전체로 보내면 확인 창이 뜹니다.
   승인 카드의 **🧰 … 묶음 모두 허용하고 다시 실행**: 막힌 명령이 개발 명령·파일 복사·이동 묶음에 속하면 같은 종류를 한 번에 허용해 다음부터 덜 묻습니다.
   막힌 명령·MCP 도구가 나오면 Claude 는 **그 자리에서 멈춥니다** (⏸ 표시 — 막힌 단계를 건너뛰고 다음 작업을 하지 않음).
   허용하면 **멈춘 Claude 세션을 그대로 이어서** 그 단계부터 실행합니다 (앞에서 읽은 파일·실행 결과를 기억, 처음부터 다시 하지 않음).
   토론 + 작업 모드에서 Claude 가 실행 단계에서 멈춘 경우도 토론을 다시 하지 않고 그 세션만 이어서 진행합니다.
   승인은 빨리 할수록 쌉니다 — 1시간 안이면 이전 기록을 캐시에서 읽습니다 (🔔 알림을 켜 두세요).
   **시간 제한**: 진행 상황이 계속 나오면 기다리고, **15분 동안 아무 진행이 없거나 60분**이 넘으면 멈춥니다.
   멈춰도 작업은 버리지 않습니다 — **⏱ 시간 제한으로 멈췄습니다 · ↪ 이어서 진행** 을 누르면 그 세션에서 계속합니다.
   기본 허용 목록에는 `cat`·`ls`·`grep`·`sha1sum`·`cut`·`diff`·`git show` 같은 **읽기 전용 명령**이 들어 있습니다. `for … do … done` 반복문은 허용 목록으로 허용할 수 없어, Claude에게 단순한 명령으로 나눠 실행하도록 안내합니다.
3. 허용 목록 관리: 작업 폴더 옆 **🛡** 버튼 (추가·삭제·기본값으로, **파일 복사·이동 허용** = cp·mv·copy·move·xcopy·robocopy·unzip·tar·zip, **개발 명령 한 번에 허용** = node·npm·npx·python·pip·uv·git — 누르면 방금 추가된 명령이 맨 위에 표시되고 버튼이 **✓ 개발 명령 허용됨**으로 바뀝니다). `python`·`node`·`rm`·`curl` 처럼 사실상 무엇이든 할 수 있는 명령은 빨간 표시가 붙습니다.
4. **진행 상황**: Claude가 지금 쓰는 도구·명령(🔌 블렌더 · execute_blender_code, `$ npm install` 등)이 진행 표시 아래에 실시간으로 나오고, 끝나면 답변의 **작업 기록 보기**에 남습니다.
5. **저장점(선택)**: 작업 폴더가 Git 저장소면 끝난 뒤 **📝 변경된 파일** 카드 → **✅ 확정 (커밋)** / **↩ 되돌리기**.
   저장 안 된 변경이 있으면 시작 전에 "저장점 만들고 시작 / 저장점 없이 진행"을 고릅니다. Git 저장소가 아닌 폴더(예: `D:\` 아래 새 폴더)는 그냥 진행합니다.

- **GPT(Codex)**: `workspace-write` 샌드박스 — 작업 폴더 안에서만 쓰고, 명령 실행과 **인터넷(설치 등)은 허용**됩니다. Codex는 명령별 승인을 할 수 없어 폴더 범위로 제한합니다.
- **블렌더 등 연결된 도구**: 모드와 별개로 **🔌 Claude MCP** / **🔌 GPT MCP** 를 켭니다 (각 CLI에 Blender MCP가 등록돼 있어야 함).
- **토론 + 작업 (협업)**: ① GPT·Claude가 **읽기만 하며** 계획 토론 → ② 결론 → ③ **실행: Claude / 실행: GPT** 로 고른 모델이 작업 →
  ④ 다른 모델이 결과(파일·블렌더 씬)를 **읽기 전용으로 검토**하고 끝납니다. 지적이 있으면 **🔧 지적 반영하기** 를 누를 때만
  실행했던 Claude 세션을 이어서 고칩니다 (자동으로 두 번 고치지 않음 → 토큰 절약). 구현 중 승인이 필요한 명령이 막히면 검토 전에 멈춥니다.
  화면: **토론·작업 과정 보기**(접힘: 1차 의견 → 교차 검토 → 합의한 계획 → 구현 → 결과 검토) 아래에 **🏁 최종 결과**, 그 아래 검토 상태·변경 파일.
  대화 모드 토론도 과정(접힘) 아래에 **🏁 최종 결론**이 마지막으로 보입니다. 기록은 `3_구현`·`4_검토.md`.
- **서버 실행**: 오래 켜 두는 서버는 백그라운드로 실행하도록 지시합니다. 끄는 방법은 답변에 안내됩니다.
- ⚠ **운영 중인 서비스 폴더는 복사본에서** 작업하고 확인 후 반영하는 것을 권장합니다.
- **⚠ 전체 권한 모드** (작업 폴더 옆 **🔓 전체 권한 끔/켬**, 대화별, 기본 꺼짐): 켜면 이 대화의 Claude 작업 실행이 명령·파일 수정·**작업 폴더 밖 접근**(다른 드라이브, `Z:` 등)을
  묻지 않고 실행합니다 (Claude Code `bypassPermissions`). 켤 때 위험 안내·확인 창이 뜨고, 켜져 있는 동안 입력창 위에 빨간 띠가 보입니다.
  - 적용: Claude 단독 작업, 승인·시간 제한 후 이어서, 토론의 구현·지적 반영 단계. 그대로: 대화 모드(🎨 이미지 포함), 토론의 계획·검토, GPT 샌드박스.
  - MCP 도구는 전체 권한에서도 **항상 허용한 것만** 바로 실행되고, 나머지는 지금처럼 승인 카드가 뜹니다.
  - 그 대화에만 적용 — 새 대화·새 대화로 이어가기·다른 PC 로 넘어가지 않습니다. 운영 서버 작업 전에는 백업을 먼저 하세요.

### 🔁 Claude 데스크톱 앱과 번갈아 쓰기
세션(대화)을 넘기기보다 **같은 작업 폴더 + 인수인계 기록**으로 이어 가는 방식입니다.
1. 작업 폴더 옆 **📄** → `CLAUDE.md` 준비 (없으면 프로젝트 안내 틀, 있으면 "HANDOFF.md 에 기록" 규칙만 덧붙임).
   Claude Code(데스크톱 앱·터미널·Council 작업 모드)는 작업 폴더의 `CLAUDE.md` 를 자동으로 읽습니다. 짧게 유지하세요.
2. **📝 인수인계 켬** (기본): 작업 모드가 끝나면 Council 이 `HANDOFF.md` 에 요청·실행 모델·상태·바뀐 파일·세션 ID·결과 요약을 덧붙입니다.
   파일을 읽기만 한 질문은 기록하지 않습니다. ⚠ 웹 서버가 그대로 공개하는 폴더(운영 중인 사이트 폴더 등)라면 끄세요.
3. Claude 작업 답변의 **🖥 Claude 앱에서 이어서**: 데스크톱 앱에서 그 세션을 바로 엽니다 (`claude://resume?session=…`, 공식 문서에 없는 링크).
   안 열리면 데스크톱 앱 Code 화면에서 `/resume` → 세션 선택, 또는 복사된 터미널 명령 `claude --resume <ID>`.
4. **대화 모드 답변·토론 결론**에는 **🖥 Claude 앱으로 가져가기**: 질문·결론(토론이면 1차 의견 요약 포함)·앞선 맥락을 한 문서로 **복사**하고
   `exports\handoff\` 에 파일로도 저장합니다. Claude 데스크톱 앱 새 대화에 붙여넣으면(Ctrl+V) 이어집니다 (대화 모드는 Claude Code 세션이 없어 문서로 넘김).
5. 앱에서 한 작업은 Council 대화에 들어오지 않습니다. Council 로 돌아올 때는 **"HANDOFF.md 마지막 항목 보고 이어서 해줘"**.
- 같은 폴더를 Council 과 앱에서 **동시에** 작업시키지 마세요. Git 저장소면 넘기기 전에 ✅ 확정(커밋)해 두면 안전합니다.

### 🎨 대화 중 이미지 (대화 모드)
예전 🎨 이미지 모드는 V0.26.0 에서 대화 모드로 합쳐졌습니다 (모드 버튼은 💬 대화 · 🛠 작업 두 개).
- 대화 모드 입력창 위 **🎨 이미지 켬** → 대상이 GPT 로 바뀌고, 대화하다가 "○○ 그려줘"라고 하면 GPT 가 바로 만들어 **이 대화에 보여 줍니다**.
- 켜면 옆에 **비율**(**16:9** 기본 · 1:1 · 9:16 · 4:3 · 3:4 · **묻기**)과 **장수**(1~4장)가 나타납니다.
  **묻기**를 고르면 비율을 말하지 않은 새 이미지는 GPT 가 만들기 전에 어떤 비율로 할지 먼저 물어봅니다.
  실제 크기는 이미지 모델이 지원하는 크기 중 가장 가까운 것으로 만들어지며, 이미지 아래에 픽셀 크기(예: `1536×1024`)가 표시됩니다.
- 이어서 "하늘을 더 어둡게"처럼 말하면 **방금 만든 이미지를 보고 고칩니다**. Claude 로 바꿔 "방금 만든 이미지 어때?"라고 물으면 Claude 가 이미지를 보고 답합니다.
- **⬇ 다운로드**: 이미지마다 아래에 다운로드 버튼. **📁 폴더 열기**로 저장 폴더를 엽니다. 📎로 이미지를 첨부하면 참고 이미지로 씁니다.
- **저장 폴더**: 기본은 Council 폴더의 `image` (예: `D:\AI-Council\image`, GitHub 제외). 왼쪽 위 **⚙ 환경설정**에서 바꿀 수 있습니다 (기본값으로 · 📁 폴더 열기).
  파일 이름은 `council_날짜_시각_1.png …`.
- 이미지를 요청하지 않은 질문에는 평소처럼 답만 합니다. 이미지 생성은 GPT(ChatGPT **Plus 이상**, 구독 사용량)만 되고, 장당 30초~1분 걸립니다.
- 이미지가 안 만들어지면 왼쪽 아래에서 Codex CLI를 최신으로 업데이트한 뒤 다시 시도하세요.

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
| 작업 중 `오류: network error` | 화면과 서버의 연결이 끊긴 것입니다. Council 이 자동으로 확인해 **서버가 꺼졌으면** "1_AI Council 실행"으로 다시 켜라고, **작업이 계속 중이면** 끝날 때 자동으로 보여 줍니다. 그동안 그 대화는 작업 중이라 전체 권한 켜기 등은 끝난 뒤에 됩니다 |
| `Selected model is at capacity` / `Overloaded` | 모델 서버가 일시적으로 붐빔 (사용량 한도 아님). 대화 모드는 15초 뒤 한 번 자동 재시도 — 계속되면 잠시 후 다시 보내거나 **모델 설정**에서 다른 모델·계정 기본값 선택 |
| `Failed to authenticate: OAuth session expired` / 로그인 만료 | 왼쪽 아래 **버전 다시 확인** → 빨간 **로그인하기** (또는 터미널 `claude auth login` / `codex login`) 후 다시 보내기 |
| GPT 모델 오류 (`not supported … ChatGPT account`) | 모델 설정에서 GPT를 **계정 기본값** 으로 |
| 한쪽 구독만 있음 | 그 모델만 선택해서 사용 (토론은 두 구독이 모두 필요) |

## 🔒 저장 위치 · 보안

- Council 서버는 이 PC 의 화면만 받습니다: 주소(Host)가 `127.0.0.1`/`localhost` 가 아니거나, 다른 웹사이트(Origin)에서 보낸 요청, JSON 이 아닌 API 요청은 거절합니다 (403/415).

| 경로 | 내용 |
|---|---|
| `data/conversations/` | 대화 원문(`.jsonl`, 추가만 함)과 제목·요약 등 메타 정보 |
| `data/attachments/` | 첨부 원본 |
| `data/debates/` | 토론 기록 (`질문.md`, `1_GPT.md`, `1_Claude.md`, `2_*_검토.md`, `결론.md`) |
| `data/trash/` | 삭제한 대화 (복구 가능, 영구 삭제 시 첨부·토론 기록도 삭제) |
| `data/cli_state.json` | 사용 횟수, 계정 기본 모델 이름 |
| `data/mcp_settings.json`, `data/mcp_state.json` | MCP "항상 허용" 도구, 마지막으로 확인한 도구 목록 |
| `data/settings.json` | ⚙ 환경설정 (이미지 저장 폴더, 창 열기 방식) |
| `image/` | 🎨 대화 중 이미지 기본 저장 폴더 (⚙ 환경설정에서 변경) |
| `exports/` | Markdown 내보내기 |

- `data/`, `exports/`, `image/` 는 **GitHub에 올라가지 않습니다** (`.gitignore`).
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
| `council_image.py` | 🎨 대화 중 이미지: 생성 결과 저장·비율 안내·픽셀 크기 |
| `council_settings.py` | ⚙ 환경설정 (`data/settings.json`: 이미지 저장 폴더, 창 열기 방식) |
| `council_app.py` | 🖥 앱 창(Edge/Chrome `--app`)으로 열기, 실행 바로가기 만들기 (Windows 바탕화면·시작 메뉴, Mac `~/Applications/AI Council.app`) · 아이콘 `assets/` |
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

> **Current version: V0.27.0** · [Changelog (Korean)](CHANGELOG.md) · [한국어 설명은 위로 ↑](#ai-council)

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
- **⚠ Full access mode** (per chat, off by default, confirmation required, red banner while on) — Claude's Work-mode runs in that chat use `bypassPermissions`: commands, file edits and access outside the working folder (other drives, `Z:`) run without asking. Only Claude's work execution steps are affected (not Chat/Image modes, discussion planning/review, or GPT's sandbox); MCP tools still need "Always allow". Not carried into new chats or other PCs.
- **Local-only server** — requests with a foreign Host, a cross-site Origin or a non-JSON body are refused (403/415).
- **Command allowlist + approval** — allowlisted commands (`mkdir`, `ls`, `git status` …) run right away; any other command is blocked and shown below the answer with **Allow once / Always allow / Don't allow**. Codex runs in its `workspace-write` sandbox (writes inside the folder only; internet allowed for installs).
- **Optional Git checkpoint** — if the folder is a Git repository, review the changed files and diff afterwards, then **commit** or **revert** with one click.
- **🌐 Web search** toggle — both models search the web and cite sources
- **🎨 Images in chat** — in Chat mode turn on **🎨 Images**: ask GPT for an image mid-conversation and it appears right in the chat; follow-ups like "make the sky darker" edit the image it just made, and Claude can look at it and comment. Pick the ratio (**16:9** by default, 1:1, 9:16, 4:3, 3:4, or **Ask** = GPT asks the ratio first) and count (1–4); each image has **⬇ Download** and its pixel size. Saved to the `image` folder inside the Council folder by default — change it in **⚙ Settings** (top left). The old 🎨 Image mode was merged into this in V0.26.0.
- **🔌 Claude MCP / GPT MCP** — use connected tools such as Blender with either model. Claude: only tools you allow run automatically, others ask first. GPT: all tools registered in Codex are enabled when on.
- **Collaboration** — Discussion + Work: both plan → the model you pick (**Run: Claude / Run: GPT**) executes → the other reviews the actual result read-only and it stops there; **🔧 Apply review** continues the executor's Claude session only when you click it (no automatic second pass). The steps are collapsed above, and the **🏁 Final result** (or **🏁 Final conclusion** in a chat discussion) comes last.
- **Attachments** — text/JSON, images, video (12 frames via ffmpeg), ZIP (safely extracted: file list, text/code contents, up to 8 images; in work mode the extracted folder can be opened); drag & drop or Ctrl+V. ComfyUI workflow JSON is pre-summarized (nodes, models, color-coded required inputs)
- **💰 Token saving** — always on: the start of the recent-context window stays fixed so each prompt begins like the previous one and hits the CLIs' prompt cache (cached input counts much cheaper); older discussions keep only the conclusion; the final summary uses a short context; images are re-sent only when the question is about them. Every answer shows 🪙 tokens (new input / cached input / output), with daily totals at the bottom left. Optional **💰 Saver** toggle: skips the discussion cross review (5 → 3 calls), shorter context and attachment excerpts, concise answers, low reasoning effort for GPT in chat.
- **🔁 Switching with the Claude desktop app** — 📄 prepares `CLAUDE.md` (template, or just appends the handoff rule); 📝 Handoff (on by default) appends request / status / changed files / session ID / result summary to `HANDOFF.md` in the working folder after each Work task (read-only questions are skipped; turn it off for folders a web server publishes); **🖥 Continue in Claude app** opens the session in the desktop app via `claude://resume?session=…` (undocumented link; fallback: `/resume` in the app or the copied `claude --resume <ID>`). Chat-mode answers and discussion conclusions get **🖥 Take to Claude app**: the question, conclusion (plus round-1 excerpts) and earlier context are copied as one document (also saved under `exports/handoff/`) to paste into a new chat in the desktop app. Back in Council, say "read the last entry of HANDOFF.md and continue".
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

- **Run**: the **AI Council** icon on the Desktop / in the Start menu (Mac: the **AI Council** app in ~/Applications; or `1_AI Council 실행 (Windows).cmd` / `(Mac).command`). The server starts in the background and Council opens in an **app window** (no address bar or tabs, via Edge/Chrome) at `http://127.0.0.1:8765` — reachable from this computer only. Existing installs: **⚙ Settings → Create shortcut**. Pin it from the Start menu (right-click → Pin to taskbar) or drag the Mac app to the Dock. Prefer a tab? **⚙ Settings → Open Council in: Browser tab**.
- **Update**: when a new version exists, a yellow **⬆ Update** appears at the bottom left → **Update now**. Or run `2_업데이트 (Windows).cmd` / `(Mac).command` ("update"; same as `Update.cmd` / `Update-mac.command`). Your conversations are kept.
- **Stop**: **Quit app** at the bottom left. Closing the window (or tab) leaves the server running.

## 🧭 Using it

- **Mode**: 💬 Chat (no file access) · 🛠 Work (reads, creates and edits files and runs commands in the working folder)
- **📁＋ Additional folders** (Work mode): click 📁＋ next to the working folder to add more folders to read and edit (separate with `;`, up to 10; `--add-dir` for Claude and Codex). Commands, `HANDOFF.md` and the Git checkpoint still use the main working folder.
- **Target**: GPT · Claude · Discussion (both debate → neutral conclusion; *Show debate rounds* expands each round)
- **Work mode**: if a command is blocked even though it is allowed (Claude Code's own safety checks: paths outside the working folder, a whole drive as the working folder, protected folders), Council shows the reason instead of repeating the same approval card; use a project folder (e.g. `D:\VQC`) rather than a whole drive. The approval card offers **🧰 Allow all dev commands / file copy/move and run again** when the blocked command belongs to one of those groups, so you get asked less next time. When a command or MCP tool is blocked, Claude **pauses right there** (⏸, nothing after it runs) and a 🛡 card appears — **Allow once and run again** / **Always allow and run again** resumes the same Claude session from that step (also for the executor step in Discussion + Work, without rerunning the discussion). Approve soon: within about an hour the earlier history is read from cache. Time limit: Claude keeps going while it reports progress; it stops after 15 minutes with no progress or 60 minutes in total, and **↪ Continue** resumes the same session (work is not thrown away). Manage the allowlist with **🛡** next to the folder. In a Git repository you can review changes and **✅ Commit** or **↩ Revert**; with uncommitted changes you choose **Create checkpoint and start** or **Continue without**.
- **💰 Saver on/off** (fewer tokens: see Features), **Web search on/off**, **Claude MCP / GPT MCP on/off** (⚙ manages Claude's always-allowed tools), **Run: Claude / Run: GPT** in Discussion + Work, **Models ▾** to pin model versions
- **⤓ MD** downloads one answer; **Chat_md** downloads the whole chat; **■ Stop** (or Esc) stops generating
- **Long chats**: only the latest 12 turns are drawn (⬆ show earlier / show all); **🗜 Compress** summarizes the chat now; **↪ Continue in new chat** starts a new chat that carries over a summary.
- **🔔 Notifications**: desktop notification when an answer is ready (or needs approval) while you're in another window; toggle with 🔔/🔕 at the top left.
- **Language**: `EN` / `한국어` at the top left. Saved messages are not translated; only Council's own labels and messages change.

## 🔒 Privacy

- Everything is stored locally in `data/` (conversations, attachments, debate logs, settings), `exports/` and `image/` (generated images). All are git-ignored and never uploaded to GitHub.
- The models still run in the cloud: your questions and attachments are sent to **OpenAI / Anthropic** under your own account's terms.
- AI Council never uses API keys and never falls back to an API when a CLI fails.

## 💻 For developers

- Python 3.10+ **standard library only**; the whole UI is a single file, `web/index.html`.
- Tests use fake CLIs (no real model calls): `python tests/test_api.py`, `python tests/test_update.py`, `python tests/test_docs.py`
- Contribution rules for humans and coding agents: [`CLAUDE.md`](CLAUDE.md) (= `AGENTS.md`, Korean).
