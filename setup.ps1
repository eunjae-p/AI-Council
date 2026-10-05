# AI Council 설치 도우미 (Windows PowerShell 5.1 / PowerShell 7 호환)
# Setup.cmd 를 더블클릭하면 실행됩니다. 관리자 권한은 필요 없습니다.
# 하는 일: Python, Node.js, Git, Codex CLI, Claude Code 확인/설치 → 로그인 안내 → 바탕화면 바로가기

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Results = New-Object System.Collections.ArrayList

function Write-Step($text) { Write-Host ""; Write-Host "▶ $text" -ForegroundColor Cyan }
function Write-Ok($text)   { Write-Host "  ✓ $text" -ForegroundColor Green }
function Write-Warn($text) { Write-Host "  ! $text" -ForegroundColor Yellow }
function Write-Bad($text)  { Write-Host "  ✗ $text" -ForegroundColor Red }
function Add-Result($name, $status, $note) { [void]$Results.Add([pscustomobject]@{ 항목 = $name; 결과 = $status; 메모 = $note }) }

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
        Write-Bad "winget 이 없어 자동 설치할 수 없습니다. 직접 설치하세요: $url"
        return $false
    }
    Write-Host "  winget 으로 $label 설치 중... (몇 분 걸릴 수 있습니다)"
    & winget install -e --id $id --scope user --accept-package-agreements --accept-source-agreements --silent
    if ($LASTEXITCODE -ne 0) {
        # 일부 패키지는 사용자 범위 설치를 지원하지 않음 → 기본 범위로 재시도
        & winget install -e --id $id --accept-package-agreements --accept-source-agreements --silent
    }
    Update-SessionPath
    return $true
}

Write-Host "======================================" -ForegroundColor White
Write-Host "  AI Council 설치 도우미" -ForegroundColor White
Write-Host "======================================" -ForegroundColor White
Write-Host "이미 설치된 항목은 건너뜁니다. 인터넷 연결이 필요합니다."
Update-SessionPath

# 1) Python ------------------------------------------------------------
Write-Step "1/6 Python 확인"
$py = Find-Command 'python'
if (-not $py) {
    Install-WithWinget 'Python.Python.3.12' 'Python 3.12' 'https://www.python.org/downloads/' | Out-Null
    $py = Find-Command 'python'
}
if ($py) {
    $v = Get-Version $py.Source '--version'
    if ($v -and [version]$v -lt [version]'3.10.0') {
        Write-Warn "Python $v 는 너무 오래되었습니다. 3.10 이상을 설치하세요: https://www.python.org/downloads/"
        Add-Result 'Python' '업데이트 필요' "현재 $v"
    } else { Write-Ok "Python $v"; Add-Result 'Python' 'OK' $v }
} else {
    Write-Bad "Python 을 찾을 수 없습니다. 설치 후 이 창을 닫고 Setup.cmd 를 다시 실행하세요."
    Add-Result 'Python' '실패' 'https://www.python.org/downloads/ (Add python.exe to PATH 체크)'
}

# 2) Node.js (Codex CLI 설치용) ------------------------------------------
Write-Step "2/6 Node.js 확인 (Codex CLI 설치에 필요)"
$node = Find-Command 'node'
if (-not $node) {
    Install-WithWinget 'OpenJS.NodeJS.LTS' 'Node.js LTS' 'https://nodejs.org/' | Out-Null
    $node = Find-Command 'node'
}
if ($node) { $v = Get-Version $node.Source '--version'; Write-Ok "Node.js $v"; Add-Result 'Node.js' 'OK' $v }
else { Write-Bad "Node.js 를 찾을 수 없습니다."; Add-Result 'Node.js' '실패' 'https://nodejs.org/ 에서 LTS 설치' }

# 3) Git (Council 업데이트 버튼에 필요) -----------------------------------
Write-Step "3/6 Git 확인 (Council 자체 업데이트에 필요)"
$git = Find-Command 'git'
if (-not $git) {
    Install-WithWinget 'Git.Git' 'Git' 'https://git-scm.com/download/win' | Out-Null
    $git = Find-Command 'git'
}
if ($git) { $v = Get-Version $git.Source '--version'; Write-Ok "Git $v"; Add-Result 'Git' 'OK' $v }
else { Write-Warn "Git 이 없으면 Council 업데이트 버튼을 쓸 수 없습니다."; Add-Result 'Git' '권장' 'https://git-scm.com/download/win' }
if ($git -and -not (Test-Path (Join-Path $Root '.git'))) {
    Write-Warn "이 폴더는 ZIP 으로 받은 것 같습니다. 업데이트 기능을 쓰려면 'git clone https://github.com/eunjae-p/AI-Council.git' 으로 받으세요."
}

# 3) Codex CLI ---------------------------------------------------------
Write-Step "4/6 Codex CLI 설치/업데이트 (GPT 연결용)"
$npm = Find-Command 'npm'
if ($npm) {
    & $npm.Source install -g '@openai/codex@latest'
    Update-SessionPath
}
$codex = Find-Command 'codex'
if ($codex) { $v = Get-Version $codex.Source '--version'; Write-Ok "Codex CLI $v"; Add-Result 'Codex CLI' 'OK' $v }
else { Write-Bad "Codex CLI 설치 실패"; Add-Result 'Codex CLI' '실패' "Node.js 설치 후 'npm i -g @openai/codex@latest'" }

# 4) Claude Code -------------------------------------------------------
Write-Step "5/6 Claude Code 확인 (Claude 연결용)"
$claude = Find-Command 'claude'
if (-not $claude) {
    Write-Host "  공식 설치 프로그램으로 설치 중... (자동 업데이트되는 방식)"
    try {
        Invoke-RestMethod 'https://claude.ai/install.ps1' | Invoke-Expression
    } catch { Write-Bad "설치 프로그램 실행 실패: $($_.Exception.Message)" }
    # 설치 폴더를 사용자 PATH 에 등록 (없을 때만)
    $bin = "$env:USERPROFILE\.local\bin"
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    if ((Test-Path $bin) -and ($userPath -notlike "*$bin*")) {
        [Environment]::SetEnvironmentVariable('Path', (($userPath, $bin) | Where-Object { $_ }) -join ';', 'User')
        Write-Ok "PATH 에 $bin 추가"
    }
    Update-SessionPath
    $claude = Find-Command 'claude'
}
if ($claude) { $v = Get-Version $claude.Source '--version'; Write-Ok "Claude Code $v"; Add-Result 'Claude Code' 'OK' $v }
else { Write-Bad "Claude Code 설치 실패"; Add-Result 'Claude Code' '실패' 'https://code.claude.com/docs 의 설치 안내 참고' }

# 5) 로그인 -------------------------------------------------------------
Write-Step "6/6 로그인 확인 (각자 자기 구독 계정, 브라우저에서 진행)"
if ($codex) {
    & $codex.Source login status *> $null
    if ($LASTEXITCODE -eq 0) { Write-Ok "Codex: 로그인됨"; Add-Result 'Codex 로그인' 'OK' '' }
    else {
        $ans = Read-Host "  Codex(ChatGPT 계정) 로그인이 필요합니다. 지금 로그인할까요? (Y/n)"
        if ($ans -ne 'n' -and $ans -ne 'N') { & $codex.Source login }
        & $codex.Source login status *> $null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Codex: 로그인됨"; Add-Result 'Codex 로그인' 'OK' '' }
        else { Write-Warn "Codex 로그인 안 됨"; Add-Result 'Codex 로그인' '필요' "터미널에서 'codex login'" }
    }
}
if ($claude) {
    & $claude.Source auth status *> $null
    if ($LASTEXITCODE -eq 0) { Write-Ok "Claude: 로그인됨"; Add-Result 'Claude 로그인' 'OK' '' }
    else {
        $ans = Read-Host "  Claude(Claude 구독 계정) 로그인이 필요합니다. 지금 로그인할까요? (Y/n)"
        if ($ans -ne 'n' -and $ans -ne 'N') { & $claude.Source auth login }
        & $claude.Source auth status *> $null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Claude: 로그인됨"; Add-Result 'Claude 로그인' 'OK' '' }
        else { Write-Warn "Claude 로그인 안 됨"; Add-Result 'Claude 로그인' '필요' "터미널에서 'claude auth login'" }
    }
}

# 바탕화면 바로가기 ------------------------------------------------------
try {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut((Join-Path $desktop 'AI Council.lnk'))
    $lnk.TargetPath = Join-Path $Root 'AI-Council_Web.cmd'
    $lnk.WorkingDirectory = $Root
    $lnk.Save()
    Write-Ok "바탕화면에 'AI Council' 바로가기를 만들었습니다."
} catch { Write-Warn "바로가기를 만들지 못했습니다: $($_.Exception.Message)" }

# 요약 ---------------------------------------------------------------
Write-Host ""
Write-Host "============ 설치 결과 ============" -ForegroundColor White
$Results | Format-Table -AutoSize | Out-String | Write-Host
$failed = @($Results | Where-Object { $_.결과 -ne 'OK' })
if ($failed.Count -eq 0) {
    Write-Host "모든 준비가 끝났습니다. 바탕화면의 'AI Council' 을 실행하세요." -ForegroundColor Green
} else {
    Write-Host "위 표에서 OK 가 아닌 항목을 해결한 뒤 Setup.cmd 를 다시 실행하세요." -ForegroundColor Yellow
    Write-Host "새로 설치한 프로그램이 인식되지 않으면 이 창을 닫고 다시 실행하면 됩니다." -ForegroundColor Yellow
}
