# AI Council 설치 도우미 (Windows PowerShell 5.1 / PowerShell 7 호환)
# Setup.cmd 를 더블클릭하면 실행됩니다. 관리자 권한은 필요 없습니다.
# 하는 일: Python, Node.js, Git, ffmpeg, Codex CLI, Claude Code 확인/설치 → 로그인 안내 → 바탕화면 바로가기

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Results = New-Object System.Collections.ArrayList

# 화면 언어: AI_COUNCIL_LANG(ko|en) → Windows 표시 언어/지역 → 그 외는 영어
$script:KO = $false
$langPref = "$env:AI_COUNCIL_LANG".Trim().ToLower()
if ($langPref.StartsWith('ko')) { $script:KO = $true }
elseif ($langPref.StartsWith('en')) { $script:KO = $false }
else {
    try { if ((Get-UICulture).Name -like 'ko*' -or (Get-Culture).Name -like 'ko*') { $script:KO = $true } } catch {}
}
function T($ko, $en) { if ($script:KO) { $ko } else { $en } }
# 예/아니오: 빈 입력·y·yes·예·ㅛ 는 예, n·no 는 아니오
function Test-Yes($ans) { return ("$ans".Trim().ToLower() -notin @('n', 'no')) }

function Write-Step($text) { Write-Host ""; Write-Host "▶ $text" -ForegroundColor Cyan }
function Write-Ok($text)   { Write-Host "  ✓ $text" -ForegroundColor Green }
function Write-Warn($text) { Write-Host "  ! $text" -ForegroundColor Yellow }
function Write-Bad($text)  { Write-Host "  ✗ $text" -ForegroundColor Red }
function Add-Result($name, $status, $note) { [void]$Results.Add([pscustomobject]@{ Name = $name; Status = $status; Note = $note }) }

function Update-SessionPath {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $extra = @("$env:USERPROFILE\.local\bin", "$env:APPDATA\npm")
    $env:Path = (@($machine, $user) + $extra | Where-Object { $_ }) -join ';'
}

function Find-Command($name) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $cmd) { return $null }
    # Microsoft Store 의 가짜 python.exe (WindowsApps) 는 제외
    if ($cmd.Source -like '*\WindowsApps\*') { return $null }
    return $cmd
}

function Get-Version($exe, $arg) {
    try {
        $out = & $exe $arg 2>&1 | Out-String
        if ($out -match '(\d+\.\d+\.\d+)') { return $Matches[1] }
    } catch {}
    return ''
}

function Test-Winget { return [bool](Get-Command winget -ErrorAction SilentlyContinue) }

function Install-WithWinget($id, $label, $url) {
    if (-not (Test-Winget)) {
        Write-Bad (T "winget 이 없어 자동 설치할 수 없습니다. 직접 설치하세요: $url" "winget is not available, so this cannot be installed automatically. Please install it manually: $url")
        return $false
    }
    Write-Host (T "  winget 으로 $label 설치 중... (몇 분 걸릴 수 있습니다)" "  Installing $label with winget... (this may take a few minutes)")
    & winget install -e --id $id --scope user --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) {
        # 일부 패키지는 사용자 범위 설치를 지원하지 않음 → 기본 범위로 재시도
        & winget install -e --id $id --accept-package-agreements --accept-source-agreements --silent
    }
    Update-SessionPath
    return $true
}

Write-Host "======================================" -ForegroundColor White
Write-Host (T "  AI Council 설치 도우미" "  AI Council Setup") -ForegroundColor White
Write-Host "======================================" -ForegroundColor White
Write-Host (T "이미 설치된 항목은 건너뜁니다. 인터넷 연결이 필요합니다." "Items that are already installed will be skipped. An internet connection is required.")
Update-SessionPath

# 1) Python ------------------------------------------------------------
Write-Step (T "1/7 Python 확인" "1/7 Checking Python")
$py = Find-Command 'python'
if (-not $py) {
    Install-WithWinget 'Python.Python.3.12' 'Python 3.12' 'https://www.python.org/downloads/' | Out-Null
    $py = Find-Command 'python'
}
if ($py) {
    $v = Get-Version $py.Source '--version'
    if ($v -and [version]$v -lt [version]'3.10.0') {
        Write-Warn (T "Python $v 는 너무 오래되었습니다. 3.10 이상을 설치하세요: https://www.python.org/downloads/" "Python $v is too old. Please install 3.10 or later: https://www.python.org/downloads/")
        Add-Result 'Python' (T '업데이트 필요' 'Update needed') (T "현재 $v" "current $v")
    } else { Write-Ok "Python $v"; Add-Result 'Python' 'OK' $v }
} else {
    Write-Bad (T "Python 을 찾을 수 없습니다. 설치 후 이 창을 닫고 Setup.cmd 를 다시 실행하세요." "Python not found. After installing it, close this window and run Setup.cmd again.")
    Add-Result 'Python' (T '실패' 'Failed') (T 'https://www.python.org/downloads/ (Add python.exe to PATH 체크)' 'https://www.python.org/downloads/ (check "Add python.exe to PATH")')
}

# 2) Node.js (Codex CLI 설치용) ------------------------------------------
Write-Step (T "2/7 Node.js 확인 (Codex CLI 설치에 필요)" "2/7 Checking Node.js (needed to install Codex CLI)")
$node = Find-Command 'node'
if (-not $node) {
    Install-WithWinget 'OpenJS.NodeJS.LTS' 'Node.js LTS' 'https://nodejs.org/' | Out-Null
    $node = Find-Command 'node'
}
if ($node) { $v = Get-Version $node.Source '--version'; Write-Ok "Node.js $v"; Add-Result 'Node.js' 'OK' $v }
else { Write-Bad (T "Node.js 를 찾을 수 없습니다." "Node.js not found."); Add-Result 'Node.js' (T '실패' 'Failed') (T 'https://nodejs.org/ 에서 LTS 설치' 'Install the LTS from https://nodejs.org/') }

# 3) Git (Council 업데이트 버튼에 필요) -----------------------------------
Write-Step (T "3/7 Git 확인 (Council 자체 업데이트에 필요)" "3/7 Checking Git (needed for Council self-update)")
$git = Find-Command 'git'
if (-not $git) {
    Install-WithWinget 'Git.Git' 'Git' 'https://git-scm.com/download/win' | Out-Null
    $git = Find-Command 'git'
}
if ($git) { $v = Get-Version $git.Source '--version'; Write-Ok "Git $v"; Add-Result 'Git' 'OK' $v }
else { Write-Warn (T "Git 이 없으면 Council 업데이트 버튼을 쓸 수 없습니다." "Without Git, the Council update button will not work."); Add-Result 'Git' (T '권장' 'Recommended') 'https://git-scm.com/download/win' }
if ($git -and -not (Test-Path (Join-Path $Root '.git'))) {
    Write-Warn (T "이 폴더는 ZIP 으로 받은 것 같습니다. 업데이트 기능을 쓰려면 'git clone https://github.com/eunjae-p/AI-Council.git' 으로 받으세요." "This folder looks like it was downloaded as a ZIP. To use the update feature, get it with 'git clone https://github.com/eunjae-p/AI-Council.git'.")
}

# 4) ffmpeg (영상 첨부 분석용) --------------------------------------------
Write-Step (T "4/7 ffmpeg 확인 (영상 첨부를 프레임으로 나눠 분석할 때 필요)" "4/7 Checking ffmpeg (needed to split video attachments into frames for analysis)")
$ff = Find-Command 'ffmpeg'
if (-not $ff) {
    Install-WithWinget 'Gyan.FFmpeg' 'ffmpeg' 'https://www.gyan.dev/ffmpeg/builds/' | Out-Null
    $ff = Find-Command 'ffmpeg'
}
if ($ff) { $v = Get-Version $ff.Source '-version'; Write-Ok "ffmpeg $v"; Add-Result 'ffmpeg' 'OK' $v }
else { Write-Warn (T "ffmpeg 이 없으면 영상 분석만 쓸 수 없습니다 (이미지·텍스트는 가능)." "Without ffmpeg, only video analysis is unavailable (images and text still work)."); Add-Result 'ffmpeg' (T '권장' 'Recommended') 'winget install Gyan.FFmpeg' }

# 3) Codex CLI ---------------------------------------------------------
Write-Step (T "5/7 Codex CLI 설치/업데이트 (GPT 연결용)" "5/7 Installing/updating Codex CLI (for GPT)")
$npm = Find-Command 'npm'
if ($npm) {
    & $npm.Source install -g '@openai/codex@latest'
    Update-SessionPath
}
$codex = Find-Command 'codex'
if ($codex) { $v = Get-Version $codex.Source '--version'; Write-Ok "Codex CLI $v"; Add-Result 'Codex CLI' 'OK' $v }
else { Write-Bad (T "Codex CLI 설치 실패" "Codex CLI installation failed"); Add-Result 'Codex CLI' (T '실패' 'Failed') (T "Node.js 설치 후 'npm.cmd i -g @openai/codex@latest'" "After installing Node.js: 'npm.cmd i -g @openai/codex@latest'") }

# 4) Claude Code -------------------------------------------------------
Write-Step (T "6/7 Claude Code 확인 (Claude 연결용)" "6/7 Checking Claude Code (for Claude)")
$claude = Find-Command 'claude'
if (-not $claude) {
    Write-Host (T "  공식 설치 프로그램으로 설치 중... (자동 업데이트되는 방식)" "  Installing with the official installer... (auto-updating)")
    try {
        Invoke-RestMethod 'https://claude.ai/install.ps1' | Invoke-Expression
    } catch { Write-Bad ((T "설치 프로그램 실행 실패: " "Installer failed: ") + $_.Exception.Message) }
    # 설치 폴더를 사용자 PATH 에 등록 (없을 때만)
    $bin = "$env:USERPROFILE\.local\bin"
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ((Test-Path $bin) -and ($userPath -notlike "*$bin*")) {
        [Environment]::SetEnvironmentVariable('Path', (($userPath, $bin) | Where-Object { $_ }) -join ';', 'User')
        Write-Ok (T "PATH 에 $bin 추가" "Added $bin to PATH")
    }
    Update-SessionPath
    $claude = Find-Command 'claude'
}
if ($claude) { $v = Get-Version $claude.Source '--version'; Write-Ok "Claude Code $v"; Add-Result 'Claude Code' 'OK' $v }
else { Write-Bad (T "Claude Code 설치 실패" "Claude Code installation failed"); Add-Result 'Claude Code' (T '실패' 'Failed') (T 'https://code.claude.com/docs 의 설치 안내 참고' 'See the install guide at https://code.claude.com/docs') }

# 5) 로그인 -------------------------------------------------------------
Write-Step (T "7/7 로그인 확인 (각자 자기 구독 계정, 브라우저에서 진행)" "7/7 Checking sign-in (each person uses their own subscription, in the browser)")
if ($codex) {
    & $codex.Source login status *> $null
    if ($LASTEXITCODE -eq 0) { Write-Ok (T "Codex: 로그인됨" "Codex: signed in"); Add-Result (T 'Codex 로그인' 'Codex login') 'OK' '' }
    else {
        $ans = Read-Host (T "  Codex(ChatGPT 계정) 로그인이 필요합니다. 지금 로그인할까요? (Y/n)" "  Codex (ChatGPT account) sign-in is required. Sign in now? (Y/n)")
        if (Test-Yes $ans) { & $codex.Source login }
        & $codex.Source login status *> $null
        if ($LASTEXITCODE -eq 0) { Write-Ok (T "Codex: 로그인됨" "Codex: signed in"); Add-Result (T 'Codex 로그인' 'Codex login') 'OK' '' }
        else { Write-Warn (T "Codex 로그인 안 됨" "Codex not signed in"); Add-Result (T 'Codex 로그인' 'Codex login') (T '필요' 'Needed') (T "터미널에서 'codex.cmd login'" "Run 'codex.cmd login' in a terminal") }
    }
}
if ($claude) {
    & $claude.Source auth status *> $null
    if ($LASTEXITCODE -eq 0) { Write-Ok (T "Claude: 로그인됨" "Claude: signed in"); Add-Result (T 'Claude 로그인' 'Claude login') 'OK' '' }
    else {
        $ans = Read-Host (T "  Claude(Claude 구독 계정) 로그인이 필요합니다. 지금 로그인할까요? (Y/n)" "  Claude (Claude subscription account) sign-in is required. Sign in now? (Y/n)")
        if (Test-Yes $ans) { & $claude.Source auth login }
        & $claude.Source auth status *> $null
        if ($LASTEXITCODE -eq 0) { Write-Ok (T "Claude: 로그인됨" "Claude: signed in"); Add-Result (T 'Claude 로그인' 'Claude login') 'OK' '' }
        else { Write-Warn (T "Claude 로그인 안 됨" "Claude not signed in"); Add-Result (T 'Claude 로그인' 'Claude login') (T '필요' 'Needed') (T "터미널에서 'claude auth login'" "Run 'claude auth login' in a terminal") }
    }
}

# 바탕화면 바로가기 ------------------------------------------------------
try {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut((Join-Path $desktop 'AI Council.lnk'))
    # 창 없이 실행: pythonw 를 직접 실행 (없으면 .cmd 를 최소화 창으로)
    $pyw = Find-Command 'pythonw'
    if ($pyw) {
        $lnk.TargetPath = $pyw.Source
        $lnk.Arguments = '"' + (Join-Path $Root 'ai_council_web.py') + '"'
        $lnk.IconLocation = $pyw.Source + ',0'
    } else {
        $lnk.TargetPath = Join-Path $Root 'AI-Council_Web.cmd'
        $lnk.WindowStyle = 7
    }
    $lnk.WorkingDirectory = $Root
    $lnk.Save()
    Write-Ok (T "바탕화면에 'AI Council' 바로가기를 만들었습니다." "Created an 'AI Council' shortcut on your Desktop.")
} catch { Write-Warn ((T "바로가기를 만들지 못했습니다: " "Could not create the shortcut: ") + $_.Exception.Message) }

# 요약 ---------------------------------------------------------------
Write-Host ""
Write-Host (T "============ 설치 결과 ============" "============ Setup results ============") -ForegroundColor White
$Results | Select-Object @{ n = (T '항목' 'Item'); e = { $_.Name } }, @{ n = (T '결과' 'Result'); e = { $_.Status } }, @{ n = (T '메모' 'Note'); e = { $_.Note } } |
    Format-Table -AutoSize | Out-String | Write-Host
$failed = @($Results | Where-Object { $_.Status -ne 'OK' })
if ($failed.Count -eq 0) {
    Write-Host (T "모든 준비가 끝났습니다. 바탕화면의 'AI Council' 을 실행하세요." "All set. Run 'AI Council' from your Desktop.") -ForegroundColor Green
} else {
    Write-Host (T "위 표에서 OK 가 아닌 항목을 해결한 뒤 Setup.cmd 를 다시 실행하세요." "Fix the items above that are not OK, then run Setup.cmd again.") -ForegroundColor Yellow
    Write-Host (T "새로 설치한 프로그램이 인식되지 않으면 이 창을 닫고 다시 실행하면 됩니다." "If newly installed programs are not detected, close this window and run it again.") -ForegroundColor Yellow
}
