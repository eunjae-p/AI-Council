"""화면 언어(한국어/English) — 서버가 보내는 안내·오류 문구 번역.

원칙
- 서버 코드와 대화 기록에는 지금처럼 한국어 문구를 쓰고 저장한다 (기록은 다시 쓰지 않음).
- 브라우저가 `X-Lang: en` 을 보내면 응답(JSON·스트림)을 내보내기 직전에 영어로 바꾼다 (localize).
- 번역표에 없는 문구는 한국어 그대로 보인다. CLI 원본 로그(stderr 등)는 번역하지 않는다.
- 문구를 새로 추가하면 PAIRS 에 영어도 한 줄 추가한다. `{이름}` 자리는 그대로 옮겨지고,
  그 안에 다시 한국어 문구가 있으면 그것도 번역된다.
"""
from __future__ import annotations

import re

LANGS = ("ko", "en")

# (한국어 원문, English) — 원문 전체가 일치해야 바뀐다.
# {x} 등 소문자 한 글자 = 임의의 내용, {a}·{b} = 한글이 없는 내용 (CLI 이름 등).
PAIRS: list[tuple[str, str]] = [
    # --- 요청·대화 ---
    ("요청이 너무 큽니다.", "The request is too large."),
    ("잘못된 요청입니다.", "Invalid request."),
    ("잘못된 목록 범위입니다.", "Invalid list scope."),
    ("잘못된 대화 ID입니다.", "Invalid conversation ID."),
    ("대화를 찾을 수 없습니다.", "Conversation not found."),
    ("대화를 찾을 수 없습니다. 목록을 새로고침하세요.", "Conversation not found. Refresh the list."),
    ("제목을 입력하세요.", "Enter a title."),
    ("휴지통에 같은 ID의 대화가 이미 있습니다.", "A conversation with the same ID is already in the trash."),
    ("휴지통에서 대화를 찾을 수 없습니다.", "Conversation not found in the trash."),
    ("같은 ID의 대화가 이미 있습니다.", "A conversation with the same ID already exists."),
    ("휴지통에 있는 대화만 영구 삭제할 수 있습니다.", "Only conversations in the trash can be deleted permanently."),
    ("새 대화", "New chat"),
    ("제목 일치", "Title match"),
    ("질문을 입력하세요.", "Enter a question."),
    ("지원하지 않는 모드입니다.", "Unsupported mode."),
    ("지원하지 않는 답변 모델입니다.", "Unsupported answer model."),
    ("알 수 없는 작업입니다.", "Unknown action."),
    ("알 수 없는 CLI 입니다.", "Unknown CLI."),
    ("도구 이름이 올바르지 않습니다.", "Invalid tool name."),
    ("명령 접두어가 올바르지 않습니다.", "Invalid command prefix."),
    ("이 API는 더 이상 쓰지 않습니다. /api/chat 에 target=both(토론)를 사용하세요.",
     "This API is no longer used. Use /api/chat with target=both (discussion)."),
    ("처리 실패: {x}", "Failed: {x}"),
    ("저장 실패: {x}", "Could not save: {x}"),
    ("서버 내부 오류: {x}", "Internal server error: {x}"),
    ("이 대화는 답변을 생성하는 중입니다. 완료 후 다시 시도하세요.", "This conversation is generating an answer. Try again when it finishes."),
    ("이 대화는 이미 답변을 생성하는 중입니다.", "This conversation is already generating an answer."),
    ("진행 중인 답변이 없습니다.", "No answer is in progress."),
    ("GPT/Claude 프로그램을 업데이트하는 중입니다. 끝난 뒤 다시 보내 주세요.",
     "The GPT/Claude programs are being updated. Send again when it finishes."),
    ("작업 모드에서는 작업 폴더를 입력하세요.", "Enter a working folder for this mode."),
    ("작업 폴더를 찾을 수 없습니다: {x}", "Working folder not found: {x}"),
    ("토론 기록 폴더를 찾을 수 없습니다.", "Discussion log folder not found."),
    ("저장 폴더를 찾을 수 없습니다.", "Output folder not found."),
    ("대화를 요약하지 못했습니다. 잠시 후 다시 시도하세요.", "Could not summarize the conversation. Please try again later."),
    ("{x} (이어서)", "{x} (continued)"),
    # --- 진행 단계 (stage) ---
    ("대화 맥락을 준비하는 중", "Preparing conversation context"),
    ("영상에서 프레임을 뽑는 중", "Extracting frames from the video"),
    ("첨부 파일을 분석하는 중", "Analyzing attachments"),
    ("{x}가 답변하는 중 (웹 검색 사용)", "{x} is answering (web search on)"),
    ("{x}가 답변하는 중", "{x} is answering"),
    ("1라운드 · GPT와 Claude가 각자 독립적으로 답변하는 중 (웹 검색 사용)",
     "Round 1 · GPT and Claude are answering independently (web search on)"),
    ("1라운드 · GPT와 Claude가 각자 독립적으로 답변하는 중", "Round 1 · GPT and Claude are answering independently"),
    ("2라운드 · 서로의 답변을 읽고 교차 검토하는 중", "Round 2 · Each model is reviewing the other's answer"),
    ("토론 내용을 최종 결론으로 정리하는 중", "Writing the final conclusion"),
    ("결론대로 Claude가 파일을 수정하는 중", "Claude is editing files according to the conclusion"),
    ("결론대로 {x}가 작업하는 중", "{x} is carrying out the conclusion"),
    ("승인한 내용으로 Claude가 이어서 작업하는 중", "Claude is continuing with what you approved"),
    ("Claude가 이미지 프롬프트를 쓰는 중", "Claude is writing the image prompt"),
    ("GPT가 이미지를 생성하는 중 (장당 30초~1분)", "GPT is generating the image (30 s – 1 min each)"),
    ("이미지 파일이 만들어지지 않았습니다. GPT가 이미지 생성 도구를 쓰지 못했을 수 있습니다 (ChatGPT Plus 이상 구독, Codex CLI 최신 버전 필요). 왼쪽 아래에서 Codex를 업데이트한 뒤 다시 시도하세요.",
     "No image file was created. GPT may not have been able to use its image tool (needs ChatGPT Plus or higher and the latest Codex CLI). Update Codex at the bottom left and try again."),
    ("{x}가 결과를 검토하는 중", "{x} is reviewing the result"),
    ("검토 내용을 반영해 {x}가 수정하는 중", "{x} is applying the review"),
    ("{x} 구현", "{x} implementation"),
    ("{x} 검토", "{x} review"),
    ("{x} 수정", "{x} fix"),
    # --- 스트림 안내 ---
    ("오래된 대화를 장기 요약으로 정리했습니다 ({x}).", "Older messages were condensed into a long-term summary ({x})."),
    ("장기 요약 갱신에 실패했습니다. 원문은 그대로이며 최근 대화만으로 답변합니다.",
     "Could not update the long-term summary. The original messages are kept; answering from recent messages only."),
    ("{x} CLI가 웹 검색을 지원하지 않아 검색 없이 답했습니다. 왼쪽 아래에서 CLI를 업데이트하세요.",
     "{x} CLI does not support web search, so it answered without searching. Update the CLI at the bottom left."),
    ("변경 내용을 확인하지 못했습니다: {x}", "Could not read the changes: {x}"),
    ("영상 분석을 준비하지 못해 모델에 보내지 않았습니다.", "The video could not be prepared for analysis, so nothing was sent to the models."),
    ("ZIP 파일을 풀지 못해 모델에 보내지 않았습니다.", "The ZIP file could not be extracted, so nothing was sent to the models."),
    ("ZIP 파일을 푸는 중", "Extracting the ZIP file"),
    ("{x}: 이미지(png·jpg·webp·gif·bmp), 영상(mp4·mov·mkv·avi·webm 등), ZIP 만 올릴 수 있습니다.",
     "{x}: only images (png, jpg, webp, gif, bmp), videos (mp4, mov, mkv, avi, webm …) and ZIP files can be uploaded."),
    ("{x}: 파일이 너무 큽니다 (이미지 최대 20MB, 영상 최대 2GB, ZIP 최대 500MB).",
     "{x}: file too large (images up to 20MB, videos up to 2GB, ZIP up to 500MB)."),
    ("{x}: 지원하지 않는 형식입니다. (JSON·텍스트·이미지·영상·ZIP 만 가능)",
     "{x}: unsupported format (JSON, text, image, video or ZIP only)."),
    ("ZIP 안에 풀 수 있는 파일이 없습니다.", "The ZIP contains no files that can be extracted."),
    ("ZIP 파일을 열 수 없습니다 (손상되었거나 ZIP 형식이 아님): {x}", "Cannot open the ZIP file (damaged or not a ZIP): {x}"),
    ("ZIP 안의 항목이 너무 많습니다 ({x}개, 최대 {y}개).", "Too many entries in the ZIP ({x}; max {y})."),
    ("첨부한 파일을 분석해줘.", "Please analyze the attached file(s)."),
    # --- 기록 (오류·중지·변경) ---
    ("사용자가 답변 생성을 중지했습니다 (방법: {x} · 중지 시점: {y} · 경과 {m}분 {s}초).{z}",
     "You stopped the answer (method: {x} · stopped at: {y} · elapsed {m}m {s}s).{z}"),
    ("사용자가 답변 생성을 중지했습니다 (중지 시점: {y} · 경과 {m}분 {s}초).{z}",
     "You stopped the answer (stopped at: {y} · elapsed {m}m {s}s).{z}"),
    ("사용자가 답변 생성을 중지했습니다.", "You stopped the answer."),
    (" 완료된 답변: {x}.", " Finished answers: {x}."),
    ("Esc 키", "Esc key"),
    ("■ 중지 버튼", "■ Stop button"),
    ("중지 요청", "stop request"),
    ("모든 모델 호출이 실패했습니다.\n\n{x}", "All model calls failed.\n\n{x}"),
    ("일부 모델 호출이 실패했습니다.\n\n{x}", "Some model calls failed.\n\n{x}"),
    ("{x} 교차 검토", "{x} cross review"),
    ("Claude 구현", "Claude implementation"),
    ("변경된 파일 {x}개: {y}", "{x} changed file(s): {y}"),
    ("변경을 확정했습니다 (커밋 {x}).", "Changes committed ({x})."),
    ("변경을 되돌렸습니다 (수정 전 상태로 복구).", "Changes reverted (restored to the checkpoint)."),
    ("변경 기록을 찾을 수 없습니다.", "Change record not found."),
    ("이미 확정하거나 되돌린 변경입니다.", "These changes were already committed or reverted."),
    ("중립 정리(이름 가림) · Claude · {x}", "Neutral summary (blinded) · Claude · {x}"),
    ("중립 정리(이름 가림) · Claude", "Neutral summary (blinded) · Claude"),
    ("기본값 {x}", "default {x}"),
    ("{x} 요약 실패 ({y}): {z}", "{x} summary failed ({y}): {z}"),
    # --- 수정 모드 ---
    ("수정 모드를 시작할 수 없습니다: {x} 먼저 저장점을 만드세요.", "Cannot start edit mode: {x} Create a checkpoint first."),
    ("Git 저장소가 아닙니다.", "Not a Git repository."),
    ("저장되지 않은 변경 사항이 있습니다.", "There are uncommitted changes."),
    ("아직 커밋이 없습니다.", "There are no commits yet."),
    ("Git이 설치되어 있지 않습니다. 설치 도우미(Setup)를 다시 실행하세요.", "Git is not installed. Run the setup helper again."),
    ("git {x} 실패: {y}", "git {x} failed: {y}"),
    # --- CLI 실행 ---
    ("{x} CLI를 찾을 수 없습니다. PATH 설정을 확인하세요.", "{x} CLI not found. Check your PATH."),
    ("{x} 실행 실패: {y}", "Could not run {x}: {y}"),
    ("{x}초 제한 시간을 초과했습니다.", "Timed out after {x} seconds."),
    ("종료 코드 {x}", "exit code {x}"),
    ("CLI가 빈 응답을 반환했습니다.", "The CLI returned an empty response."),
    ("Claude가 오류를 반환했습니다.", "Claude returned an error."),
    ("{a}: {y}", "{a}: {y}"),  # "claude: 종료 코드 1" 처럼 CLI 이름 + 메시지
    ("→ {x}", "→ {x}"),
    ("설치된 Codex CLI가 이 모델을 모릅니다(구버전 가능성). 터미널에서 'npm i -g @openai/codex@latest' 로 업데이트한 뒤 AI Council을 다시 시작하세요.",
     "The installed Codex CLI does not know this model (probably outdated). Update it with 'npm i -g @openai/codex@latest' and restart AI Council."),
    ("설치된 Claude Code가 이 모델을 지원하지 않는 구버전입니다. 터미널에서 'claude update' 를 실행한 뒤 AI Council을 다시 시작하세요. 그 전까지는 모델을 '계정 기본값'으로 두세요.",
     "The installed Claude Code is too old for this model. Run 'claude update' and restart AI Council. Until then, keep the model on 'Account default'."),
    ("이 GPT 모델은 ChatGPT 구독 계정의 Codex에서 거절되었습니다. '계정 기본값'에서도 같은 오류라면 %USERPROFILE%\\.codex\\config.toml 의 model 설정 때문이니, 그 값을 바꾸거나 '모델 설정 → 직접 입력'으로 동작하는 모델을 지정하세요.",
     "This GPT model was rejected by Codex for ChatGPT accounts. If 'Account default' fails the same way, the model setting in %USERPROFILE%\\.codex\\config.toml is the cause: change it, or pick a working model under 'Models → Custom'."),
    ("{x} CLI 로그인이 필요합니다. 터미널에서 {y} 로그인 후 다시 시도하세요.", "{x} CLI needs sign-in. Sign in to {y} and try again."),
    ("{x} 로그인이 만료되었거나 필요합니다. Council 왼쪽 아래 '버전 다시 확인' → 빨간 '로그인하기'를 누르거나, 터미널에서 '{y}' 를 실행한 뒤 다시 보내세요.",
     "{x} sign-in has expired or is required. Click 'Check versions again' at the bottom left → the red 'Sign in', or run '{y}' in a terminal, then send again."),
    ("구독 사용량 한도에 도달했을 수 있습니다. 잠시 후 다시 시도하거나 다른 모델을 선택하세요.",
     "You may have reached your subscription usage limit. Try again later or choose another model."),
    ("MCP 목록을 가져오지 못했습니다. Claude 로그인 상태와 CLI 버전을 확인하세요.",
     "Could not load the MCP tool list. Check your Claude sign-in and CLI version."),
    # --- 첨부·영상 ---
    ("{x}: 이미지(png·jpg·webp·gif·bmp) 또는 영상(mp4·mov·mkv·avi·webm 등)만 올릴 수 있습니다.",
     "{x}: only images (png, jpg, webp, gif, bmp) or videos (mp4, mov, mkv, avi, webm …) can be uploaded."),
    ("빈 파일입니다.", "The file is empty."),
    ("{x}: 파일이 너무 큽니다 (이미지 최대 20MB, 영상 최대 2GB).", "{x}: file too large (images up to 20MB, videos up to 2GB)."),
    ("업로드가 중간에 끊겼습니다.", "The upload was interrupted."),
    ("첨부 형식이 올바르지 않습니다.", "Invalid attachment format."),
    ("첨부는 한 번에 {x}개까지 가능합니다.", "Up to {x} attachments at a time."),
    ("첨부 파일 정보가 올바르지 않습니다.", "Invalid attachment info."),
    ("{x}: 업로드된 파일을 찾을 수 없습니다. 다시 첨부해 주세요.", "{x}: uploaded file not found. Please attach it again."),
    ("{x}: 지원하지 않는 형식입니다.", "{x}: unsupported format."),
    ("{x}: 텍스트 파일만 첨부할 수 있습니다.", "{x}: only text files can be attached."),
    ("{x}: 지원하지 않는 형식입니다. (JSON·텍스트·이미지·영상만 가능)", "{x}: unsupported format (JSON, text, images and videos only)."),
    ("{x}: 파일이 너무 큽니다 (최대 약 2MB).", "{x}: file too large (about 2MB max)."),
    ("영상 {x}: 분석 준비 실패 — {y}", "Video {x}: could not prepare for analysis — {y}"),
    ("이 PC에 ffmpeg가 없어 영상을 분석할 수 없습니다. Council 폴더의 {x}를 실행해 ffmpeg를 설치한 뒤 Council을 다시 시작하세요. (이미지·텍스트 첨부는 ffmpeg 없이도 됩니다)",
     "ffmpeg is not installed, so videos cannot be analyzed. Run {x} in the Council folder to install it, then restart Council. (Images and text work without ffmpeg.)"),
    ("영상 정보를 읽지 못했습니다: {x}", "Could not read video info: {x}"),
    ("영상에서 프레임을 뽑지 못했습니다. 코덱이 지원되지 않을 수 있습니다.", "Could not extract frames from the video. The codec may be unsupported."),
    ("# 영상 정보: {x}", "# Video info: {x}"),
    ("- 오디오: {x} (소리는 분석 대상이 아님)", "- Audio: {x} (sound is not analyzed)"),
    ("이미지 {x}", "Image {x}"),
    # --- CLI 버전·업데이트·로그인 ---
    ("Node.js(npm)를 찾을 수 없습니다. Council 폴더의 {x}를 실행해 설치하세요.", "Node.js (npm) not found. Run {x} in the Council folder to install it."),
    ("CLI 파일이 사용 중이라 바꾸지 못했습니다. 다른 터미널에서 실행 중인 codex/claude를 모두 닫고 다시 시도하세요.",
     "The CLI files are in use. Close any codex/claude running in other terminals and try again."),
    ("프로그램 경로를 실행하지 못했습니다. Council을 최신 버전으로 업데이트한 뒤 다시 시도하세요.",
     "Could not run the program path. Update Council to the latest version and try again."),
    ("설치 폴더에 쓸 권한이 없습니다. {x}를 다시 실행하거나 담당자에게 문의하세요.",
     "No permission to write to the install folder. Run {x} again or ask your administrator."),
    ("인터넷 연결 문제로 받지 못했습니다. 회사 네트워크(방화벽)에서 막혔을 수 있습니다.",
     "Download failed because of a network problem. A firewall may be blocking it."),
    ("아래 기록을 확인하세요. 계속 실패하면 {x}를 다시 실행해 보세요.", "Check the log below. If it keeps failing, run {x} again."),
    ("{x}분 안에 끝나지 않아 중단했습니다.", "Stopped: did not finish within {x} minutes."),
    ("실행 실패: {x}", "Could not run: {x}"),
    ("답변을 생성하는 중에는 업데이트할 수 없습니다. 완료되거나 중지한 뒤 다시 시도하세요.",
     "Cannot update while an answer is being generated. Wait or stop it, then try again."),
    ("이미 업데이트가 진행 중입니다. 잠시 기다려 주세요.", "An update is already running. Please wait."),
    ("답변 생성 중에는 계정을 바꿀 수 없습니다. 끝나거나 중지한 뒤 다시 시도하세요.",
     "Cannot switch accounts while an answer is being generated. Wait or stop it, then try again."),
    # --- Council 자체 업데이트 ---
    ("Git이 설치되어 있지 않습니다. {x}를 다시 실행하거나 https://git-scm.com 에서 설치하세요.",
     "Git is not installed. Run {x} again or install it from https://git-scm.com."),
    ("Git으로 설치되지 않은 폴더라 자동 업데이트를 할 수 없습니다. GitHub에서 'git clone'으로 다시 받으면 업데이트 기능을 쓸 수 있습니다.",
     "This folder was not installed with Git, so it cannot auto-update. Download again with 'git clone' to enable updates."),
    ("GitHub 연결 시간이 초과되었습니다. 인터넷 연결을 확인하세요.", "Timed out connecting to GitHub. Check your internet connection."),
    ("Git으로 설치되지 않은 폴더입니다. GitHub에서 git clone으로 다시 받아 주세요.",
     "This folder was not installed with Git. Download it again with git clone."),
    ("이 PC에 GitHub에 없는 커밋이 {x}개 있습니다. 먼저 GitHub에 올리거나 정리한 뒤 업데이트하세요.",
     "This computer has {x} commit(s) that are not on GitHub. Push or clean them up first, then update."),
    ("이 PC에서 직접 수정된 파일이 있어 업데이트를 멈췄습니다 (덮어쓰지 않음):\n{x}",
     "Update stopped because files were edited on this computer (nothing was overwritten):\n{x}"),
]

_HANGUL = re.compile(r"[가-힣]")
_SLOT = re.compile(r"\{([a-z])\}")


def _compile(ko: str) -> re.Pattern:
    out, pos = [], 0
    for m in _SLOT.finditer(ko):
        out.append(re.escape(ko[pos:m.start()]))
        body = r"[^가-힣\n]*?" if m.group(1) in "ab" else ".*?"
        out.append(f"(?P<{m.group(1)}>{body})")
        pos = m.end()
    out.append(re.escape(ko[pos:]))
    return re.compile("".join(out) + r"\Z", re.S)


# 구체적인(빈칸이 적고 고정 글자가 많은) 문구를 먼저 시도한다
_TABLE = sorted(((_compile(ko), en, len(_SLOT.sub("", ko))) for ko, en in PAIRS), key=lambda t: -t[2])


def _whole(text: str, depth: int) -> str | None:
    for pattern, en, _ in _TABLE:
        m = pattern.match(text)
        if m:
            groups = {k: (tr(v, "en", depth + 1) if v else v) for k, v in m.groupdict().items()}
            return _SLOT.sub(lambda s: groups.get(s.group(1), ""), en)
    return None


def tr(text: str, lang: str = "en", depth: int = 0) -> str:
    """한국어 서버 문구 → 영어. 일치하는 문구가 없으면 줄 단위로 다시 시도하고, 그래도 없으면 그대로."""
    if lang != "en" or not isinstance(text, str) or not _HANGUL.search(text) or depth > 6:
        return text
    hit = _whole(text, depth)
    if hit is not None:
        return hit
    if "\n" in text:
        return "\n".join(tr(line, lang, depth + 1) for line in text.split("\n"))
    return text


# 번역하는 키 — 모델 답변·사용자 글(content, title 등)은 건드리지 않는다
_KEYS = {"error", "message", "hint", "text", "summary_error", "output", "cli_model", "snippet"}
_RECORD_ROLES = {"edit", "error"}  # 서버가 쓴 기록만 content 를 번역


def localize(value: object, lang: str) -> object:
    if lang != "en":
        return value
    if isinstance(value, list):
        return [localize(v, lang) for v in value]
    if not isinstance(value, dict):
        return value
    out = {}
    for k, v in value.items():
        if isinstance(v, str):
            if k in _KEYS or (k == "content" and value.get("role") in _RECORD_ROLES) or (k == "title" and v == "새 대화"):
                v = tr(v, lang)
            elif k == "content" and value.get("role") == "user" and v == "첨부한 파일을 분석해줘.":
                v = tr(v, lang)
        else:
            v = localize(v, lang)
        out[k] = v
    return out


def request_lang(headers) -> str:
    value = (headers.get("X-Lang") or "").strip().lower()
    return value if value in LANGS else "ko"
